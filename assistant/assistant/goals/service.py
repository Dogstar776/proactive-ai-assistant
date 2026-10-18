"""目标服务：自省报告 → 模板合成 → 入队（论文 3.3）。

一次 synthesize() 把一份自省报告的缺口经模板编译为目标对象，
以启发式 Ĝ 近似排序入统一队列；同一 (报告, 模板, 标题) 重复合成幂等。
"""
from __future__ import annotations

from assistant.charter import Charter
from assistant.events.bus import EventBus
from assistant.goals.repository import Goal, GoalRepository, heuristic_priority, new_goal_id
from assistant.goals.templates import DEFAULT_TEMPLATES, GoalTemplate
from assistant.introspection.service import IntrospectionReport
from assistant.logging_setup import get_logger

logger = get_logger("goals")


class GoalService:
    def __init__(
        self,
        repo: GoalRepository,
        charter: Charter,
        bus: EventBus,
        templates: list[GoalTemplate] | None = None,
    ) -> None:
        self.repo = repo
        self.charter = charter
        self.bus = bus
        # 注意：必须用 is not None 判断——空列表是合法输入（OQ7 模板移除测试
        # 依赖"显式移除全部模板"），用 `or` 会把 [] 误当默认值。
        self.templates = templates if templates is not None else DEFAULT_TEMPLATES

    def synthesize(self, report: IntrospectionReport) -> list[Goal]:
        """把自省报告的缺口合成为目标并入库。返回新入队的目标。"""
        inserted: list[Goal] = []
        for tpl in self.templates:
            for draft in tpl.match(report.gaps, self.charter):
                goal = Goal(
                    # 确定性 ID：同一模板 + 同一标题 → 同一目标（跨周期幂等，
                    # 重复检测时刷新而非重复入队）
                    goal_id=new_goal_id(tpl.template_id, draft.title),
                    title=draft.title,
                    description=draft.description,
                    template_id=draft.template_id,
                    status="active",
                    priority=heuristic_priority(draft.info_gain, draft.practical_value),
                    info_gain=draft.info_gain,
                    practical_value=draft.practical_value,
                    risk_level=draft.risk_level,
                    success_criteria=draft.success_criteria,
                    source_report=report.report_id,
                    source_gaps=draft.source_gaps,
                    due_at=draft.due_at,
                    metadata=draft.metadata,
                )
                if self.repo.insert(goal):
                    inserted.append(goal)
                    logger.info(
                        "goal.enqueued template=%s priority=%.3f title=%s",
                        goal.template_id, goal.priority, goal.title,
                    )
        return inserted

    def list_goals(self, status: str | None = "active", limit: int = 50) -> list[dict]:
        return [vars(g) for g in self.repo.list(status=status, limit=limit)]

    def stats(self) -> dict:
        return {
            "by_status": self.repo.count_by_status(),
            "templates": [t.template_id for t in self.templates],
        }

    def set_status(self, goal_id: str, status: str) -> None:
        self.repo.update_status(goal_id, status)
