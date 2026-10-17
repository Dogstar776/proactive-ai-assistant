"""本地规则抽取器：不调用 LLM 的归一化 + 重要度启发式。

规则是显式、可审查的——这正是论文 5.2 所说的"判据问题转移给规则设计者"，
本项目如实标注 extractor=rules，并在 OQ7 模板移除测试中测量其边界。
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

from assistant.extraction.base import Extractor
from assistant.models import ExtractedEvent, RawItem

_URGENT_WORDS = ("紧急", "截止", "deadline", "面试", "汇报", "逾期", "asap", "urgent")
_SOON_DAYS = 7  # 事件时间落在 N 天内 → 提升重要度


def _urgency_hint(raw: RawItem) -> float:
    text = f"{raw.title} {raw.content}".lower()
    hits = sum(1 for w in _URGENT_WORDS if w in text)
    score = min(hits * 0.25, 0.5)
    if raw.event_time:
        try:
            when = datetime.fromisoformat(raw.event_time)
            days = (when - datetime.now(UTC)).total_seconds() / 86400
            if 0 <= days <= _SOON_DAYS:
                score += 0.4
            elif days < 0:
                score += 0.3  # 已过期事项仍有跟进价值
        except ValueError:
            pass
    return min(score, 1.0)


class RulesExtractor(Extractor):
    name = "rules"

    def extract(self, raw: RawItem) -> ExtractedEvent:
        content = re.sub(r"\s+", " ", raw.content).strip()
        summary = content[:120] + ("…" if len(content) > 120 else "")
        tags = [raw.kind]
        if raw.metadata.get("location"):
            tags.append("has_location")
        return ExtractedEvent(
            kind=raw.kind,
            title=raw.title.strip(),
            summary=summary,
            content=content,
            event_time=raw.event_time,
            importance=round(_urgency_hint(raw), 3),
            tags=tags,
            extractor=self.name,
            metadata={**raw.metadata, "extracted_by": "rules"},
        )
