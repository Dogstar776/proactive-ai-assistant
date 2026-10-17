"""MockLLM：确定性的"假模型"。

存在意义（ADR-0005）：开源复现不需要任何密钥即可跑通全链路；
输出携带 `mock:true` 标记与确定性的"伪摘要"，绝不伪装成真实模型推理。
"""
from __future__ import annotations

import hashlib

from assistant.extraction.base import Extractor
from assistant.models import ExtractedEvent, RawItem


class MockLlmExtractor(Extractor):
    name = "mock_llm"

    def extract(self, raw: RawItem) -> ExtractedEvent:
        seed = hashlib.sha256(f"{raw.kind}|{raw.title}".encode()).hexdigest()[:6]
        summary = f"[MOCK-{seed}] {raw.title}"
        # 确定性伪重要度：由内容哈希派生，重复采集结果一致
        importance = round(int(seed[:2], 16) / 255, 3)
        return ExtractedEvent(
            kind=raw.kind,
            title=raw.title.strip(),
            summary=summary,
            content=raw.content,
            event_time=raw.event_time,
            importance=importance,
            tags=[raw.kind, "mock"],
            extractor=self.name,
            metadata={**raw.metadata, "extracted_by": "mock_llm", "mock": True},
        )
