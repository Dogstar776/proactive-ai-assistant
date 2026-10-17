"""目标队列：仓储 + 启发式 Ĝ 近似排序。

优先级公式（论文 3.3 改造 EFE 的工程近似，**不是**严格构造）：

    priority = w_info * info_gain + w_practical * practical_value

- info_gain：缺口强度（认识价值项的可计算近似候选，论文 OQ2 的起点）
- practical_value：charter 域权重归一（实用价值项必须外源锚定，论文 3.3 关键改造）

权重是显式配置的常量而非学习得到——诚实标注为启发式（ADR-0003）。
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

W_INFO = 0.6
W_PRACTICAL = 0.4

VALID_STATUS = {"active", "suspended", "done", "revoked"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Goal:
    goal_id: str
    title: str
    description: str
    template_id: str
    status: str = "active"
    priority: float = 0.0
    info_gain: float = 0.0
    practical_value: float = 0.0
    risk_level: str = "R1"
    success_criteria: str = ""
    source_report: str | None = None
    source_gaps: list[str] | None = None
    created_at: str = ""
    updated_at: str = ""
    due_at: str | None = None
    provenance: str = "template-based"
    metadata: dict | None = None

    @classmethod
    def from_row(cls, row) -> Goal:
        d = dict(row)
        d["source_gaps"] = json.loads(d.get("source_gaps") or "[]")
        d["metadata"] = json.loads(d.get("metadata") or "{}")
        return cls(**d)

    def to_row(self) -> dict:
        d = {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "template_id": self.template_id,
            "provenance": self.provenance,
            "status": self.status,
            "priority": self.priority,
            "info_gain": self.info_gain,
            "practical_value": self.practical_value,
            "risk_level": self.risk_level,
            "success_criteria": self.success_criteria,
            "source_report": self.source_report,
            "source_gaps": json.dumps(self.source_gaps or [], ensure_ascii=False),
            "created_at": self.created_at or _now(),
            "updated_at": self.updated_at or _now(),
            "due_at": self.due_at,
            "metadata": json.dumps(self.metadata or {}, ensure_ascii=False),
        }
        return d


def heuristic_priority(info_gain: float, practical_value: float) -> float:
    """启发式 Ĝ 近似：显式加权和，无学习、无隐藏项。"""
    return round(max(0.0, min(1.0, W_INFO * info_gain + W_PRACTICAL * practical_value)), 3)


class GoalRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def insert(self, goal: Goal) -> bool:
        """插入目标；已存在则刷新溯源与优先级（幂等且保鲜）。返回是否为新插入。"""
        existed = (
            self.conn.execute(
                "SELECT 1 FROM goals WHERE goal_id = ?", (goal.goal_id,)
            ).fetchone()
            is not None
        )
        self.conn.execute(
            """
            INSERT INTO goals
                (goal_id, title, description, template_id, provenance, status, priority,
                 info_gain, practical_value, risk_level, success_criteria, source_report,
                 source_gaps, created_at, updated_at, due_at, metadata)
            VALUES
                (:goal_id, :title, :description, :template_id, :provenance, :status, :priority,
                 :info_gain, :practical_value, :risk_level, :success_criteria, :source_report,
                 :source_gaps, :created_at, :updated_at, :due_at, :metadata)
            ON CONFLICT (goal_id) DO UPDATE SET
                source_report = excluded.source_report,
                priority = excluded.priority,
                info_gain = excluded.info_gain,
                practical_value = excluded.practical_value,
                updated_at = excluded.updated_at
            """,
            goal.to_row(),
        )
        self.conn.commit()
        return not existed

    def update_status(self, goal_id: str, status: str) -> None:
        if status not in VALID_STATUS:
            raise ValueError(f"非法目标状态: {status}")
        cur = self.conn.execute(
            "UPDATE goals SET status = ?, updated_at = ? WHERE goal_id = ?",
            (status, _now(), goal_id),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            from assistant.errors import NotFoundError

            raise NotFoundError(f"目标不存在: {goal_id}")

    def list(self, *, status: str | None = "active", limit: int = 50) -> list[Goal]:
        sql = "SELECT * FROM goals"
        params: list = []
        if status:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY priority DESC, created_at DESC LIMIT ?"
        params.append(limit)
        return [Goal.from_row(r) for r in self.conn.execute(sql, params)]

    def count_by_status(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) AS n FROM goals GROUP BY status")
        return {r["status"]: int(r["n"]) for r in rows}


def new_goal_id(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "|".join(parts)))
