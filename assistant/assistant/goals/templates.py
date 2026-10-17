"""目标合成模板：缺口 → 目标对象。

诚实声明（ADR-0003）：这些模板是"主动行为的模拟"中目标侧的工程近似——
目标实质是模板设计者意图的延迟执行（论文 5.2 结论一）。每个产出目标携带
`template_id` 与 `provenance=template-based`，正是 OQ7 模板移除测试的测量对象。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from assistant.charter import Charter
from assistant.introspection.detectors import Gap


@dataclass
class GoalDraft:
    title: str
    description: str
    template_id: str
    info_gain: float                  # 认识价值项近似 = 缺口强度
    practical_value: float            # 实用价值项近似 = charter 域权重
    risk_level: str = "R1"
    success_criteria: str = ""
    due_at: str | None = None
    source_gaps: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class GoalTemplate(ABC):
    template_id: str = ""
    risk_level: str = "R1"

    @abstractmethod
    def match(self, gaps: list[Gap], charter: Charter) -> list[GoalDraft]:
        ...


class DeadlinePrepTemplate(GoalTemplate):
    """截止准备：临期事项 + 无准备记录 → 只读型准备目标（R1）。"""

    template_id = "deadline-prep"
    risk_level = "R1"

    def match(self, gaps: list[Gap], charter: Charter) -> list[GoalDraft]:
        drafts = []
        for g in gaps:
            if g.kind != "deadline-prep":
                continue
            weight, domain = charter.domain_weight(g.title)
            drafts.append(GoalDraft(
                title=f"为「{self._subject(g.title)}」做截止前准备",
                description=(
                    f"{g.detail}。本目标为只读型认知目标（R1）：整理材料、列出清单，"
                    f"不涉及对外动作，不修改原始事项。"
                ),
                template_id=self.template_id,
                info_gain=g.score,
                practical_value=round(weight / 10.0, 3),
                risk_level=self.risk_level,
                success_criteria="产出一份准备材料清单，并在笔记中留下记录",
                source_gaps=[g.title],
                metadata={"gap_kind": g.kind, "matched_domain": domain, "evidence": g.evidence},
            ))
        return drafts

    @staticmethod
    def _subject(title: str) -> str:
        # 「XXX」临近（N 天）但无相关准备记录 → XXX
        start = title.find("「")
        end = title.find("」", start + 1)
        return title[start + 1:end] if 0 <= start < end else title


class ThemeClusterTemplate(GoalTemplate):
    """主题聚类：反复出现的主题 → 只读型梳理目标（R1）。"""

    template_id = "theme-cluster"
    risk_level = "R1"

    def match(self, gaps: list[Gap], charter: Charter) -> list[GoalDraft]:
        drafts = []
        for g in gaps:
            if g.kind != "theme-cluster":
                continue
            weight, domain = charter.domain_weight(g.title)
            drafts.append(GoalDraft(
                title=f"梳理「{self._subject(g.title)}」相关事项清单",
                description=(
                    f"{g.detail}。本目标为只读型认知目标（R1）：汇总相关事件、"
                    f"形成一份主题笔记，不涉及对外动作，不修改原始数据。"
                ),
                template_id=self.template_id,
                info_gain=g.score,
                practical_value=round(weight / 10.0, 3),
                risk_level=self.risk_level,
                success_criteria="形成一份主题笔记，链接相关事件",
                source_gaps=[g.title],
                metadata={"gap_kind": g.kind, "matched_domain": domain, "evidence": g.evidence},
            ))
        return drafts

    @staticmethod
    def _subject(title: str) -> str:
        start = title.find("「")
        end = title.find("」", start + 1)
        return title[start + 1:end] if 0 <= start < end else title


class ContradictionTemplate(GoalTemplate):
    """矛盾清理：过期/重复项聚合为一个只读型清理核查目标（R1）。

    聚合而非逐项：清理类目标的标题必须跨周期稳定（计数会随处理进度变化），
    否则同一目标每天换 ID 重复入队，破坏队列幂等。
    """

    template_id = "contradiction-scan"
    risk_level = "R1"

    def match(self, gaps: list[Gap], charter: Charter) -> list[GoalDraft]:
        items = [g for g in gaps if g.kind == "contradiction"]
        if not items:
            return []
        return [GoalDraft(
            title="核查并处理：过期未消与跨源重复项",
            description=(
                "；".join(g.title for g in items)
                + "。本目标为只读型认知目标（R1）：列出待处理项供人类确认，"
                "不自动改动任何原始记录。"
            ),
            template_id=self.template_id,
            info_gain=max(g.score for g in items),
            practical_value=0.3,  # 清理类目标固定低实用价值，不攀附域权重
            risk_level=self.risk_level,
            success_criteria="产出一份待确认处理清单",
            source_gaps=[g.title for g in items],
            metadata={"gap_kind": "contradiction",
                      "evidence": [e for g in items for e in g.evidence]},
        )]


DEFAULT_TEMPLATES: list[GoalTemplate] = [
    DeadlinePrepTemplate(),
    ThemeClusterTemplate(),
    ContradictionTemplate(),
]
