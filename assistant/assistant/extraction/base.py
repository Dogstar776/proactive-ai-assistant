"""抽取管道抽象：RawItem → ExtractedEvent。

两种实现：
- RulesExtractor：本地规则（默认，不调 LLM，零成本，ADR-0005 高频轻观测层）
- MockLlmExtractor：确定性假 LLM（无密钥复现；输出带 mock 标记，绝不伪装真实推理）
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from assistant.models import ExtractedEvent, RawItem


class Extractor(ABC):
    name: str = ""

    @abstractmethod
    def extract(self, raw: RawItem) -> ExtractedEvent:
        ...
