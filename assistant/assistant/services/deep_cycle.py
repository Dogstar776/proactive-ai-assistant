"""深周期编排：自省 → 目标合成 → 提醒门控（论文 3.2→3.3→3.5 的闭环一步）。

对应 ADR-0005 的"低频深周期"：默认由 API/CLI 触发，P6 起再做定时调度。
"""
from __future__ import annotations

from assistant.events.bus import EventBus
from assistant.gateway.reminder_service import ReminderService
from assistant.goals.service import GoalService
from assistant.introspection.service import IntrospectionReport, IntrospectionService


class DeepCycleService:
    def __init__(
        self,
        introspection: IntrospectionService,
        goals: GoalService,
        bus: EventBus,
        reminders: ReminderService | None = None,
    ) -> None:
        self.introspection = introspection
        self.goals = goals
        self.bus = bus
        self.reminders = reminders

    def run(self, trigger: str = "api") -> dict:
        report: IntrospectionReport = self.introspection.run_cycle(trigger=trigger)
        new_goals = self.goals.synthesize(report)
        return {
            "report_id": report.report_id,
            "trigger": report.trigger,
            "summary": report.summary,
            "gaps": [vars(g) for g in report.gaps],
            "audit": report.audit.to_dict(),
            "new_goals": [vars(g) for g in new_goals],
        }
