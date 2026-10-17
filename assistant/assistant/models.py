"""领域模型：观测事件 / 采集原始项 / 抽取结果。

所有持久化记录携带 provenance（来源）与 chain_depth（生成链深度）——
论文 4.3 / OQ4 记忆健康指标的最小可实现子集（ADR-0004）。
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

PROVENANCE_USER = "user_injected"
PROVENANCE_SYSTEM = "system_derived"
PROVENANCE_EXTERNAL = "external_retrieved"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _uuid5(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "|".join(parts)))


@dataclass
class RawItem:
    """连接器输出的原始条目（未经抽取管道）。"""

    kind: str                      # calendar_event / todo / note / feed_item
    external_id: str               # 源系统内的稳定 ID（幂等键）
    title: str
    content: str = ""
    event_time: str | None = None  # ISO8601
    metadata: dict = field(default_factory=dict)


@dataclass
class ExtractedEvent:
    """抽取管道输出：归一化后的观测事件（入库前形态）。"""

    kind: str
    title: str
    summary: str = ""
    content: str = ""
    event_time: str | None = None
    importance: float = 0.0
    tags: list[str] = field(default_factory=list)
    extractor: str = "rules"
    metadata: dict = field(default_factory=dict)


@dataclass
class ObservedEvent:
    """入库的观测事件（论文 3.1：增量状态表征的最小单元）。"""

    source: str
    source_ref: str
    consent_id: str
    kind: str
    title: str
    summary: str = ""
    content: str = ""
    event_time: str | None = None
    observed_at: str = field(default_factory=_now)
    importance: float = 0.0
    tags: list[str] = field(default_factory=list)
    extractor: str = "rules"
    provenance: str = PROVENANCE_EXTERNAL
    chain_depth: int = 0
    metadata: dict = field(default_factory=dict)
    event_id: str = ""

    def __post_init__(self) -> None:
        # 确定性 ID：同一源同一内容重复采集 → 同一 event_id → INSERT OR IGNORE 幂等
        if not self.event_id:
            digest = hashlib.sha256(
                f"{self.source}|{self.source_ref}|{self.kind}|{self.title}".encode()
            ).hexdigest()[:12]
            self.event_id = _uuid5(self.source, self.source_ref, digest)
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError("importance 必须在 [0,1]")

    def to_row(self) -> dict:
        d = asdict(self)
        d["tags"] = json.dumps(self.tags, ensure_ascii=False)
        d["metadata"] = json.dumps(self.metadata, ensure_ascii=False)
        return d

    @classmethod
    def from_row(cls, row) -> ObservedEvent:
        d = dict(row)
        d["tags"] = json.loads(d.get("tags") or "[]")
        d["metadata"] = json.loads(d.get("metadata") or "{}")
        return cls(**d)


@dataclass
class AuditEntry:
    action: str
    actor: str
    status: str
    target: str | None = None
    duration_ms: int | None = None
    detail: dict = field(default_factory=dict)
    ts: str = field(default_factory=_now)
    audit_id: str = field(default_factory=lambda: _uuid5(_now(), uuid.uuid4().hex))

    def to_row(self) -> dict:
        d = asdict(self)
        d["detail"] = json.dumps(self.detail, ensure_ascii=False)
        return d
