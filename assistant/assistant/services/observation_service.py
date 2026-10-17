"""观测服务层：编排"一次轻观测周期"与查询。

路由层（控制器）只做请求解析/响应格式化，业务规则在这里（专家规范三层架构）。
"""
from __future__ import annotations

from assistant.collectors.runner import CollectorRunner
from assistant.events.bus import EventBus
from assistant.memory.repository import AuditRepository, ConsentRepository, EventRepository
from assistant.models import AuditEntry, ObservedEvent


class ObservationService:
    def __init__(
        self,
        runner: CollectorRunner,
        events: EventRepository,
        audit: AuditRepository,
        consent: ConsentRepository,
        bus: EventBus,
    ) -> None:
        self.runner = runner
        self.events = events
        self.audit = audit
        self.consent = consent
        self.bus = bus

    def run_cycle(self, collector_id: str | None = None) -> list[dict]:
        results = self.runner.run_once(collector_id)
        return [vars(r) for r in results]

    def list_events(
        self,
        *,
        source: str | None = None,
        kind: str | None = None,
        since: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        evs = self.events.list(source=source, kind=kind, since=since, limit=limit, offset=offset)
        return [self._serialize(e) for e in evs]

    def event_stats(self) -> dict:
        return {"total": self.events.count(), "by_source": self.events.count_by_source()}

    def list_collectors(self) -> list[dict]:
        return self.runner.list_collectors()

    def list_consents(self) -> list[dict]:
        return self.consent.list()

    def revoke_consent(self, consent_id: str) -> None:
        self.consent.revoke(consent_id)
        self.audit.append(AuditEntry(
            action="consent.revoke", actor="owner", target=consent_id, status="ok",
            detail={"revoked_by": "owner"},
        ))

    def list_audit(self, *, action: str | None = None, limit: int = 100) -> list[dict]:
        return self.audit.list(action=action, limit=limit)

    def bus_stats(self) -> dict:
        return self.bus.stats()

    @staticmethod
    def _serialize(ev: ObservedEvent) -> dict:
        return {
            "event_id": ev.event_id,
            "source": ev.source,
            "source_ref": ev.source_ref,
            "kind": ev.kind,
            "title": ev.title,
            "summary": ev.summary,
            "event_time": ev.event_time,
            "observed_at": ev.observed_at,
            "importance": ev.importance,
            "tags": ev.tags,
            "extractor": ev.extractor,
            "provenance": ev.provenance,
            "chain_depth": ev.chain_depth,
        }
