"""缺口检测器：从观测事件中识别"值得注意的缺口"。

论文 3.2 声明：自省的评价基准是系统自身认知结构的完整性——这在当前技术下
不可靠（论文 4.2），因此本模块全部输出显式标注 `[B-simulated]`：
规则是显式的、可审查的，不是"模型真的在自省"。
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from assistant.models import ObservedEvent

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_STOP_BIGRAMS = {
    "我们", "可以", "一个", "这个", "那个", "已经", "如果", "之后", "之前",
    "完成", "进行", "需要", "没有", "什么", "怎么", "这样", "那么", "但是",
    "而且", "或者", "因为", "所以", "当前", "目前", "本次", "相关",
}


@dataclass
class Gap:
    kind: str                  # deadline-prep / theme-cluster / contradiction
    title: str
    detail: str
    score: float               # 0~1 缺口强度（信息增益项的近似输入）
    evidence: list[str] = field(default_factory=list)  # 相关 event_id


class GapDetector(ABC):
    kind: str = ""

    @abstractmethod
    def detect(self, events: list[ObservedEvent], *, now: datetime) -> list[Gap]:
        ...


def _parse_time(ev: ObservedEvent) -> datetime | None:
    if not ev.event_time:
        return None
    try:
        return datetime.fromisoformat(ev.event_time)
    except ValueError:
        return None


class DeadlinePrepDetector(GapDetector):
    """有明确截止时间的事项，但事件库中无相关"准备/进展"迹象 → 缺口。"""

    kind = "deadline-prep"

    def __init__(self, horizon_days: int = 7) -> None:
        self.horizon_days = horizon_days

    def detect(self, events: list[ObservedEvent], *, now: datetime) -> list[Gap]:
        prep_signals = {"note", "feed_item"}  # 笔记/阅读视为潜在准备活动
        gaps: list[Gap] = []
        for ev in events:
            when = _parse_time(ev)
            if when is None or ev.kind not in {"calendar_event", "todo"}:
                continue
            days = (when - now).total_seconds() / 86400
            if not -1 <= days <= self.horizon_days:
                continue
            related = [
                e for e in events
                if e.kind in prep_signals and e.title != ev.title
                and self._overlap(e.title, ev.title)
            ]
            if related:
                continue
            urgency = max(0.3, 1.0 - days / (self.horizon_days + 1))
            gaps.append(Gap(
                kind=self.kind,
                title=f"「{ev.title}」临近（{days:.0f} 天）但无相关准备记录",
                detail=f"事件 {ev.event_id} 类型 {ev.kind}，时间 {ev.event_time}；"
                       f"事件库中未发现标题相关的笔记/阅读记录",
                score=round(urgency, 3),
                evidence=[ev.event_id],
            ))
        return gaps

    @staticmethod
    def _overlap(a: str, b: str) -> bool:
        """标题共享 2 字以上中文片段即视为相关（无分词器的轻量近似）。"""
        grams_a = {a[i:i + 2] for i in range(len(a) - 1) if _CJK_RE.match(a[i:i + 2])}
        grams_b = {b[i:i + 2] for i in range(len(b) - 1) if _CJK_RE.match(b[i:i + 2])}
        return len(grams_a & grams_b) >= 1


class ThemeClusterDetector(GapDetector):
    """同一主题在多个事件中反复出现且未形成任何"处理记录" → 缺口。"""

    kind = "theme-cluster"

    def __init__(self, min_events: int = 2) -> None:
        self.min_events = min_events

    def detect(self, events: list[ObservedEvent], *, now: datetime) -> list[Gap]:
        counter: Counter[str] = Counter()
        owners: dict[str, list[str]] = {}
        for ev in events:
            text = f"{ev.title}{ev.content[:200]}"
            grams = {
                text[i:i + 2]
                for i in range(len(text) - 1)
                if _CJK_RE.match(text[i:i + 2]) and text[i:i + 2] not in _STOP_BIGRAMS
            }
            for g in grams:
                counter[g] += 1
                owners.setdefault(g, []).append(ev.event_id)
        gaps: list[Gap] = []
        seen: set[str] = set()
        for gram, n in counter.most_common(10):
            if n < self.min_events or gram in seen:
                continue
            # 跳过已被更长主题覆盖的片段（简单去重）
            if any(gram in s for s in seen):
                continue
            seen.add(gram)
            ids = list(dict.fromkeys(owners[gram]))
            gaps.append(Gap(
                kind=self.kind,
                title=f"主题「{gram}」在 {n} 个事件中反复出现，尚无梳理记录",
                detail=f"共现事件 {len(ids)} 个；主题聚类仅基于标题/内容二元组频次，"
                       f"不构成语义理解（[B-simulated]）",
                score=round(min(0.3 + 0.1 * n, 0.9), 3),
                evidence=ids[:10],
            ))
            if len(gaps) >= 3:
                break
        return gaps


class ContradictionDetector(GapDetector):
    """过期未消项与跨源重复项——一致性审计的缺口侧输出。"""

    kind = "contradiction"

    def detect(self, events: list[ObservedEvent], *, now: datetime) -> list[Gap]:
        gaps: list[Gap] = []
        overdue = [
            ev for ev in events
            if ev.kind == "todo" and (when := _parse_time(ev)) and when < now
        ]
        if overdue:
            gaps.append(Gap(
                kind=self.kind,
                title=f"{len(overdue)} 个待办已过截止时间仍无处理记录",
                detail="过期事项持续留在观测流中会污染后续自省与目标生成"
                       "（论文 4.3 的日常尺度表现）",
                score=round(min(0.4 + 0.1 * len(overdue), 0.9), 3),
                evidence=[e.event_id for e in overdue][:10],
            ))
        # 跨源重复：归一化标题相同
        by_title: dict[str, list[ObservedEvent]] = {}
        for ev in events:
            key = re.sub(r"\s+", "", ev.title)
            by_title.setdefault(key, []).append(ev)
        for title, group in by_title.items():
            sources = {e.source for e in group}
            if len(group) > 1 and len(sources) > 1:
                gaps.append(Gap(
                    kind=self.kind,
                    title=f"「{title[:30]}」在 {len(sources)} 个来源重复出现",
                    detail=f"来源：{sorted(sources)}；重复条目会放大检索噪声（OQ4 指标之一）",
                    score=0.5,
                    evidence=[e.event_id for e in group][:10],
                ))
        return gaps
