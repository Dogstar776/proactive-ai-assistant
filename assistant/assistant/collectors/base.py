"""采集器抽象：每个连接器必须显式声明授权范围（ConsentSpec）。

论文 P5：授权是硬约束。连接器不持有"默认允许"——
未在 consent_ledger 中登记且未被撤回的采集范围，runner 直接跳过并记审计。
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from assistant.models import RawItem


@dataclass
class ConsentSpec:
    scope: str                      # 如 "calendar:read"
    description: str
    data_locality: str = "local_only"
    revocable: bool = True


@dataclass
class CollectorConfig:
    collector_id: str               # 稳定 ID，如 "ics:interview"
    kind: str                       # ics / markdown_notes / rss
    params: dict = field(default_factory=dict)
    consent: ConsentSpec | None = None


class Collector:
    """采集器基类。子类实现 collect()，产出 RawItem 流。"""

    kind: str = ""

    def __init__(self, cfg: CollectorConfig) -> None:
        if not cfg.collector_id:
            raise ValueError("collector_id 不能为空")
        self.cfg = cfg

    @property
    def collector_id(self) -> str:
        return self.cfg.collector_id

    @property
    def consent(self) -> ConsentSpec:
        # 子类应在类属性或初始化时提供默认 ConsentSpec
        raise NotImplementedError

    def collect(self) -> Iterator[RawItem]:
        """产出本次采集的原始条目。失败抛 CollectorError 由 runner 统一记审计。"""
        raise NotImplementedError

    def describe(self) -> dict:
        return {
            "collector_id": self.collector_id,
            "kind": self.kind,
            "params": {k: str(v) for k, v in self.cfg.params.items()},
            "consent_scope": self.consent.scope,
        }
