"""采集调度器：一次"轻观测周期"的完整闭环。

采集 → 抽取 → 幂等入库 → 事件总线广播 → 审计留痕。
论文 3.5：纯认知操作默认放行但全量留痕；授权未登记/已撤回 → 跳过并记审计。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from assistant.collectors.base import Collector, CollectorConfig
from assistant.errors import CollectorError
from assistant.events.bus import EventBus
from assistant.extraction.base import Extractor
from assistant.logging_setup import get_logger
from assistant.memory.repository import AuditRepository, ConsentRepository, EventRepository
from assistant.models import AuditEntry, ObservedEvent

logger = get_logger("collectors.runner")


@dataclass
class CollectorResult:
    collector_id: str
    status: str                      # ok / skipped_revoked / error
    items_seen: int = 0
    items_inserted: int = 0
    duration_ms: int = 0
    error: str | None = None
    dead_letter: list[str] = field(default_factory=list)


class CollectorRunner:
    def __init__(
        self,
        events: EventRepository,
        audit: AuditRepository,
        consent: ConsentRepository,
        bus: EventBus,
        extractor: Extractor,
        granted_by: str = "owner",
    ) -> None:
        self.events = events
        self.audit = audit
        self.consent = consent
        self.bus = bus
        self.extractor = extractor
        self.granted_by = granted_by
        self._collectors: dict[str, Collector] = {}

    def register(self, collector: Collector) -> None:
        self._collectors[collector.collector_id] = collector

    def register_config(self, cfg: CollectorConfig, cls: type[Collector]) -> None:
        self.register(cls(cfg))

    def list_collectors(self) -> list[dict]:
        return [c.describe() for c in self._collectors.values()]

    def run_once(self, collector_id: str | None = None) -> list[CollectorResult]:
        targets = (
            [self._collectors[collector_id]]
            if collector_id
            else list(self._collectors.values())
        )
        return [self._run_one(c) for c in targets]

    def _run_one(self, collector: Collector) -> CollectorResult:
        started = time.monotonic()
        spec = collector.consent
        result = CollectorResult(collector_id=collector.collector_id, status="ok")

        # 1) 授权硬约束（论文 P5）
        consent_id = self.consent.ensure(
            collector_id=collector.collector_id,
            scope=spec.scope,
            description=spec.description,
            granted_by=self.granted_by,
        )
        if not self.consent.is_granted(consent_id):
            result.status = "skipped_revoked"
            self._audit(collector, "skipped_revoked", started,
                        detail={"reason": "consent revoked", "scope": spec.scope})
            return result

        # 2) 采集 + 抽取 + 入库
        try:
            for raw in collector.collect():
                result.items_seen += 1
                try:
                    extracted = self.extractor.extract(raw)
                    ev = ObservedEvent(
                        source=collector.kind,
                        source_ref=collector.collector_id,
                        consent_id=consent_id,
                        kind=extracted.kind,
                        title=extracted.title,
                        summary=extracted.summary,
                        content=extracted.content,
                        event_time=extracted.event_time,
                        importance=extracted.importance,
                        tags=extracted.tags,
                        extractor=extracted.extractor,
                        provenance="external_retrieved",
                        metadata=extracted.metadata,
                    )
                    if self.events.upsert(ev):
                        result.items_inserted += 1
                        self.bus.publish(ev)
                except Exception as e:  # 单条失败进死信，不中断整轮
                    result.dead_letter.append(f"{raw.kind}:{raw.external_id}: {e}")
                    logger.warning("item failed: %s (%s)", raw.external_id, e)
        except CollectorError as e:
            result.status = "error"
            result.error = e.message
        except Exception as e:  # 未预期错误同样记审计，不抛出到 API 层
            result.status = "error"
            result.error = f"unexpected: {e}"
            logger.exception("collector %s crashed", collector.collector_id)

        result.duration_ms = int((time.monotonic() - started) * 1000)
        self._audit(collector, result.status, started, detail={
            "items_seen": result.items_seen,
            "items_inserted": result.items_inserted,
            "dead_letter": result.dead_letter[:10],
            "error": result.error,
            "extractor": self.extractor.name,
        })
        log = logger.info if result.status == "ok" else logger.warning
        log("collector.run %s status=%s seen=%d inserted=%d",
            collector.collector_id, result.status, result.items_seen, result.items_inserted)
        return result

    def _audit(self, collector: Collector, status: str, started: float, *, detail: dict) -> None:
        self.audit.append(AuditEntry(
            action="collector.run",
            actor=f"collector:{collector.kind}",
            target=collector.collector_id,
            status=status,
            duration_ms=int((time.monotonic() - started) * 1000),
            detail=detail,
        ))
