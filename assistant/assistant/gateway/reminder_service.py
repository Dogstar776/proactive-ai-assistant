"""提醒引擎：目标 → 干预 → 门控 → 触达/沉默（论文 3.5 四态 + ADR-0005 成本控制）。

一个"提醒周期"做什么：
  1) 从 active 目标生成候选干预（优先级阈值以上，冷却键=goal_id）
  2) 门控四态判决（含沉默，全部留痕）
  3) act → SSE 触达；assist/ask → 入待确认队列；silence → 记录 suppressed
  4) 超时清扫：pending 超过 ask_timeout → expired（论文：超时默认不行动）
  5) 人类批准 → 触达；拒绝 → 记录

授权疲劳自检：ask 数与批准数的比率，随周期累积，供 P6 测量（论文 4.5）。
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from assistant.charter import Charter
from assistant.events.bus import EventBus
from assistant.gateway.gate import (
    STATE_ACT,
    STATE_ASSIST,
    STATE_SILENCE,
    Gateway,
    Intervention,
)
from assistant.logging_setup import get_logger
from assistant.models import ObservedEvent

logger = get_logger("gateway.reminders")

REMINDER_MIN_PRIORITY = 0.3


@dataclass
class Reminder:
    reminder_id: str
    kind: str
    title: str
    body: str
    risk_level: str
    state: str
    status: str
    decision_reason: str
    cooldown_key: str
    goal_id: str | None = None
    channel: str = "sse"
    created_at: str = ""
    updated_at: str = ""
    expires_at: str | None = None
    metadata: dict | None = None

    @classmethod
    def from_row(cls, row) -> Reminder:
        d = dict(row)
        d["metadata"] = json.loads(d.get("metadata") or "{}")
        return cls(**d)

    def to_row(self) -> dict:
        d = dict(vars(self))
        d["metadata"] = json.dumps(self.metadata or {}, ensure_ascii=False)
        return d


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ReminderRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def insert(self, r: Reminder) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO reminders
                (reminder_id, goal_id, kind, title, body, risk_level, state, status,
                 decision_reason, cooldown_key, channel, created_at, updated_at,
                 expires_at, metadata)
            VALUES
                (:reminder_id, :goal_id, :kind, :title, :body, :risk_level, :state, :status,
                 :decision_reason, :cooldown_key, :channel, :created_at, :updated_at,
                 :expires_at, :metadata)
            """,
            r.to_row(),
        )
        self.conn.commit()

    def update(self, reminder_id: str, *, status: str, reason: str = "") -> None:
        self.conn.execute(
            "UPDATE reminders SET status = ?, decision_reason = ?, updated_at = ?"
            " WHERE reminder_id = ?",
            (status, reason, _now(), reminder_id),
        )
        self.conn.commit()

    def get(self, reminder_id: str) -> Reminder | None:
        row = self.conn.execute(
            "SELECT * FROM reminders WHERE reminder_id = ?", (reminder_id,)
        ).fetchone()
        return Reminder.from_row(row) if row else None

    def list(self, *, status: str | None = None, limit: int = 50) -> list[Reminder]:
        sql = "SELECT * FROM reminders"
        params: list = []
        if status:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [Reminder.from_row(r) for r in self.conn.execute(sql, params)]

    def pending_expired(self, now: datetime) -> list[Reminder]:
        rows = self.conn.execute(
            "SELECT * FROM reminders WHERE status = 'pending' AND expires_at IS NOT NULL"
            " AND expires_at < ?",
            (now.isoformat(),),
        ).fetchall()
        return [Reminder.from_row(r) for r in rows]

    def count_since(self, ts: str) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) AS n FROM reminders WHERE created_at >= ?"
            " GROUP BY status",
            (ts,),
        )
        return {r["status"]: int(r["n"]) for r in rows}


class ReminderService:
    def __init__(
        self,
        repo: ReminderRepository,
        gateway: Gateway,
        goals,                     # GoalRepository
        charter: Charter,
        bus: EventBus,
        audit,
        min_priority: float = REMINDER_MIN_PRIORITY,
    ) -> None:
        self.repo = repo
        self.gateway = gateway
        self.goals = goals
        self.charter = charter
        self.bus = bus
        self.audit = audit
        self.min_priority = min_priority

    # ── 提醒周期 ──
    def run_cycle(self, *, now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        active_goals = self.goals.list(status="active", limit=100)
        candidates = [g for g in active_goals if g.priority >= self.min_priority]

        daily_count = self._daily_count(now)
        last_fired = self._last_fired_map()

        result = {"evaluated": 0, "act": 0, "assist": 0, "ask": 0, "silence": 0, "expired": 0}
        for goal in candidates:
            intervention = self._to_intervention(goal)
            decision = self.gateway.evaluate(
                intervention, now=now, daily_count_today=daily_count, last_fired=last_fired
            )
            result["evaluated"] += 1
            if decision.state == STATE_SILENCE:
                status = "suppressed"
                result["silence"] += 1
            elif decision.state == STATE_ACT:
                status = "delivered"
                result["act"] += 1
                daily_count += 1
                last_fired[intervention.cooldown_key] = now
            else:
                status = "pending"
                if decision.state == STATE_ASSIST:
                    result["assist"] += 1
                else:
                    result["ask"] += 1
                daily_count += 1
                last_fired[intervention.cooldown_key] = now

            reminder = Reminder(
                reminder_id=str(uuid.uuid5(
                    uuid.NAMESPACE_URL, f"{intervention.cooldown_key}|{now.date().isoformat()}"
                )),
                goal_id=goal.goal_id,
                kind=self._kind_for(goal),
                title=intervention.title,
                body=intervention.body,
                risk_level=decision.risk.level,
                state=decision.state,
                status=status,
                decision_reason=decision.reason,
                cooldown_key=intervention.cooldown_key,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
                expires_at=decision.expires_at.isoformat() if decision.expires_at else None,
                metadata={"template_id": goal.template_id, "priority": goal.priority},
            )
            self.repo.insert(reminder)
            if status == "delivered":
                self._deliver(reminder)

        # 超时清扫（论文：超时策略=默认不行动）
        for r in self.repo.pending_expired(now):
            self.repo.update(r.reminder_id, status="expired", reason="timeout_default: deny")
            result["expired"] += 1
            self._audit_expire(r, now)

        logger.info("reminders.cycle %s", result)
        return result

    # ── 人类决策 ──
    def approve(self, reminder_id: str) -> Reminder:
        r = self.repo.get(reminder_id)
        if r is None or r.status != "pending":
            from assistant.errors import ConflictError

            raise ConflictError(f"提醒不存在或不在待确认状态: {reminder_id}")
        self.repo.update(reminder_id, status="approved", reason="owner approved")
        r.status = "approved"
        self._deliver(r)
        return r

    def reject(self, reminder_id: str) -> Reminder:
        r = self.repo.get(reminder_id)
        if r is None or r.status != "pending":
            from assistant.errors import ConflictError

            raise ConflictError(f"提醒不存在或不在待确认状态: {reminder_id}")
        self.repo.update(reminder_id, status="rejected", reason="owner rejected")
        r.status = "rejected"
        return r

    def batch_decide(self, reminder_ids: list[str], action: str) -> dict:
        """批量审计：人类在场时一次审多件（抗授权疲劳，论文 4.5）。"""
        if action not in {"approve", "reject"}:
            from assistant.errors import ValidationIssue

            raise ValidationIssue("action 必须是 approve/reject")
        ok, skipped = 0, 0
        for rid in reminder_ids:
            try:
                self.approve(rid) if action == "approve" else self.reject(rid)
                ok += 1
            except Exception:
                skipped += 1
        return {"ok": ok, "skipped": skipped}

    # ── 统计 ──
    def fatigue_stats(self, *, days: int = 7) -> dict:
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        counts = self.repo.count_since(since)
        asks = counts.get("approved", 0) + counts.get("rejected", 0) + counts.get("expired", 0)
        approvals = counts.get("approved", 0)
        return {
            "window_days": days,
            "counts": counts,
            "ask_total": asks,
            "approval_rate": round(approvals / asks, 3) if asks else None,
            "note": "approval_rate 持续走低 = 授权疲劳信号（论文 4.5）",
        }

    # ── 内部 ──
    def _to_intervention(self, goal) -> Intervention:
        return Intervention(
            kind=self._kind_for(goal),
            title=goal.title,
            body=f"{goal.description}\n\n成功判据：{goal.success_criteria}",
            cooldown_key=f"goal:{goal.goal_id}",
            goal_id=goal.goal_id,
            goal_risk=goal.risk_level,
            text=f"{goal.title} {goal.description}",
        )

    @staticmethod
    def _kind_for(goal) -> str:
        return {
            "deadline-prep": "deadline_nudge",
            "theme-cluster": "theme_digest",
            "contradiction-scan": "cleanup_list",
        }.get(goal.template_id, "generic")

    def _deliver(self, r: Reminder) -> None:
        """触达渠道：SSE（仪表盘）。本地系统通知留待 P5（诚实：未做就是不写）。"""
        self.bus.publish(ObservedEvent(
            source="gateway",
            source_ref="reminder",
            consent_id="system:internal",
            kind="reminder",
            title=r.title,
            summary=r.decision_reason,
            content=r.body,
            importance=float((r.metadata or {}).get("priority", 0.0)),
            tags=["reminder", r.kind, r.risk_level],
            extractor="rules",
            provenance="system_derived",
            chain_depth=2,  # 观测→目标→提醒：二次派生
            metadata={"reminder_id": r.reminder_id, "state": r.state, "status": r.status},
        ))

    def _audit_expire(self, r: Reminder, now: datetime) -> None:
        from assistant.models import AuditEntry

        self.audit.append(AuditEntry(
            action="reminder.expired", actor="gateway", target=r.reminder_id,
            status="expired", ts=now.isoformat(),
            detail={"reason": "timeout_default: deny", "title": r.title},
        ))

    def _daily_count(self, now: datetime) -> int:
        """今日已发生的主动干预数（delivered + pending），用于预算门控。"""
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        row = self.repo.conn.execute(
            "SELECT COUNT(*) AS n FROM reminders"
            " WHERE created_at >= ? AND status IN ('delivered', 'pending')",
            (day_start.isoformat(),),
        ).fetchone()
        return int(row["n"])

    def _last_fired_map(self) -> dict[str, datetime]:
        rows = self.repo.conn.execute(
            "SELECT cooldown_key, MAX(created_at) AS last FROM reminders"
            " WHERE status IN ('delivered', 'pending') GROUP BY cooldown_key"
        ).fetchall()
        out: dict[str, datetime] = {}
        for r in rows:
            try:
                out[r["cooldown_key"]] = datetime.fromisoformat(r["last"])
            except (ValueError, TypeError):
                continue
        return out
