"""门控：沉默-询问-协助-行动四态判决（论文 3.5 / Tang et al. 2026 的工程化）。

判决顺序（先沉默条件，后放行条件）：
  1) 免打扰时段（quiet_hours）            → silence
  2) 冷却期（cooldown_key + 间隔）         → silence
  3) 每日主动干预预算（max_proactive/day） → silence
  4) 风险分级：
       R3 → ask（挂起请示，超时默认拒绝）
       R2 → assist（入待确认队列，不主动触达）
       R1 → act（自主执行并留痕）
       R0 → act（纯内部认知）

每一次判决（含沉默）都写审计日志——"该沉默时沉默"因此成为可验证行为。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from assistant.charter import Charter
from assistant.gateway.risk import RiskAssessment, assess_risk
from assistant.logging_setup import get_logger

logger = get_logger("gateway")

STATE_SILENCE = "silence"
STATE_ACT = "act"
STATE_ASSIST = "assist"
STATE_ASK = "ask"


@dataclass
class GateDecision:
    state: str                     # silence / act / assist / ask
    reason: str
    risk: RiskAssessment
    cooldown_until: datetime | None = None
    expires_at: datetime | None = None   # ask/assist 的超时时刻


@dataclass
class Intervention:
    """一次候选干预（提醒）。"""

    kind: str
    title: str
    body: str
    cooldown_key: str
    goal_id: str | None = None
    goal_risk: str | None = None
    text: str = ""                # 风险关键词扫描文本（默认标题+正文）
    metadata: dict = field(default_factory=dict)


class Gateway:
    def __init__(
        self,
        charter: Charter,
        audit,                      # AuditRepository
        ask_timeout_hours: int = 24,
    ) -> None:
        self.charter = charter
        self.audit = audit
        self.ask_timeout_hours = ask_timeout_hours

    # ── 免打扰（论文：沉默的硬约束） ──
    def _in_quiet_hours(self, now: datetime) -> str | None:
        # charter 的时间字面量是用户的本地时间；传入的 now 通常是 UTC（ aware ）
        # 必须转换到本地时区再比较，否则会出现"本地中午被判免打扰"的错位
        # （2026-10-17 冒烟实测发现并修复）。
        local = now.astimezone()
        weekday = local.strftime("%a").lower()[:3]  # mon/tue/...
        hhmm = local.strftime("%H:%M")
        for slot in self.charter.quiet_hours:
            days = [str(d).lower()[:3] for d in slot.get("days", [])]
            if weekday not in days:
                continue
            start, end = str(slot.get("from", "")), str(slot.get("to", ""))
            if not start or not end:
                continue
            if start <= end:
                if start <= hhmm < end:
                    return f"quiet_hours({weekday} {start}-{end})"
            elif hhmm >= start or hhmm < end:  # 跨午夜
                return f"quiet_hours({weekday} {start}-{end})"
        return None

    def evaluate(
        self,
        intervention: Intervention,
        *,
        now: datetime,
        daily_count_today: int,
        last_fired: dict[str, datetime],
    ) -> GateDecision:
        # 1) 免打扰
        quiet = self._in_quiet_hours(now)
        if quiet:
            return self._decide(STATE_SILENCE, quiet, intervention, now)

        # 2) 冷却期
        budget = self.charter.intervention_budget
        cooldown_min = int(budget.get("cooldown_minutes", 120))
        last = last_fired.get(intervention.cooldown_key)
        if last is not None and now - last < timedelta(minutes=cooldown_min):
            until = last + timedelta(minutes=cooldown_min)
            return self._decide(
                STATE_SILENCE, f"cooldown({cooldown_min}min, until {until:%H:%M})",
                intervention, now,
            )

        # 3) 每日预算（抗授权疲劳的第一道闸）
        cap = self.charter.max_proactive_per_day
        if daily_count_today >= cap:
            return self._decide(
                STATE_SILENCE, f"daily_budget({daily_count_today}/{cap})", intervention, now
            )

        # 4) 风险分级
        risk = assess_risk(goal_risk=intervention.goal_risk, text=intervention.text)
        if risk.level == "R3":
            return self._decide(
                STATE_ASK, "R3 高风险：挂起请示，超时默认不行动", intervention, now,
                expires=now + timedelta(hours=self.ask_timeout_hours),
            )
        if risk.level == "R2":
            return self._decide(
                STATE_ASSIST, "R2 低风险：入待确认队列，不主动触达", intervention, now,
                expires=now + timedelta(hours=self.ask_timeout_hours),
            )
        return self._decide(STATE_ACT, f"{risk.level} 放行：自主执行并留痕", intervention, now)

    def _decide(
        self,
        state: str,
        reason: str,
        intervention: Intervention,
        now: datetime,
        *,
        expires: datetime | None = None,
    ) -> GateDecision:
        risk = assess_risk(goal_risk=intervention.goal_risk, text=intervention.text)
        decision = GateDecision(state=state, reason=reason, risk=risk, expires_at=expires)
        self._audit(intervention, decision, now)
        logger.info("gate.decision state=%s reason=%s key=%s", state, reason,
                    intervention.cooldown_key)
        return decision

    def _audit(self, intervention: Intervention, decision: GateDecision, now: datetime) -> None:
        from assistant.models import AuditEntry

        self.audit.append(AuditEntry(
            action="gate.decision",
            actor="gateway",
            target=intervention.cooldown_key,
            status=decision.state,
            detail={
                "kind": intervention.kind,
                "title": intervention.title,
                "reason": decision.reason,
                "risk_level": decision.risk.level,
                "risk_reasons": decision.risk.reasons,
            },
            ts=now.isoformat(),
        ))
