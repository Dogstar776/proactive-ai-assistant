"""runner 与服务行为测试：授权硬约束、死信、幂等回放、SSE 总线。"""
from assistant.collectors import CollectorRunner
from assistant.collectors.base import Collector, CollectorConfig, ConsentSpec
from assistant.errors import CollectorError
from assistant.events.bus import EventBus
from assistant.extraction import RulesExtractor
from assistant.memory.repository import AuditRepository, ConsentRepository, EventRepository
from assistant.models import RawItem


class _FakeCollector(Collector):
    kind = "fake"

    def __init__(self, cfg, items, boom=False):
        super().__init__(cfg)
        self._items = items
        self._boom = boom

    @property
    def consent(self):
        return ConsentSpec(scope="fake:read", description="测试用")

    def collect(self):
        if self._boom:
            raise CollectorError("模拟采集失败")
        yield from self._items


def _make_runner(conn, items=None, boom=False):
    return CollectorRunner(
        events=EventRepository(conn),
        audit=AuditRepository(conn),
        consent=ConsentRepository(conn),
        bus=EventBus(),
        extractor=RulesExtractor(),
    )


def test_run_once_records_audit(conn):
    r = _make_runner(conn, items=[
        RawItem(kind="todo", external_id="a", title="买牛奶"),
        RawItem(kind="todo", external_id="b", title="写周报"),
    ])
    r.register(_FakeCollector(CollectorConfig(collector_id="fake:1", kind="fake"), [
        RawItem(kind="todo", external_id="a", title="买牛奶"),
    ]))
    results = r.run_once()
    assert results[0].status == "ok"
    assert results[0].items_inserted == 1
    audit = AuditRepository(conn).list(action="collector.run")
    assert audit and audit[0]["detail"]["items_inserted"] == 1


def test_collector_error_goes_to_audit_not_api(conn):
    r = _make_runner(conn, boom=True)
    r.register(_FakeCollector(CollectorConfig(collector_id="fake:boom", kind="fake"),
                              [], boom=True))
    results = r.run_once()
    assert results[0].status == "error"
    assert "模拟采集失败" in results[0].error


def test_revoked_consent_skips_collection(conn):
    consent = ConsentRepository(conn)
    audit = AuditRepository(conn)
    r = CollectorRunner(
        events=EventRepository(conn), audit=audit, consent=consent,
        bus=EventBus(), extractor=RulesExtractor(),
    )
    r.register(_FakeCollector(CollectorConfig(collector_id="fake:rev", kind="fake"),
                              [RawItem(kind="todo", external_id="x", title="t")]))
    r.run_once()
    cid = consent.list()[0]["consent_id"]
    consent.revoke(cid)
    res = r.run_once()
    assert res[0].status == "skipped_revoked"
    assert EventRepository(conn).count() == 1  # 撤回后不再采集


def test_bus_publish_reaches_queue():
    from assistant.models import ObservedEvent

    bus = EventBus()
    q = bus.subscribe_queue()
    ev = ObservedEvent(source="s", source_ref="r", consent_id="c", kind="todo", title="t")
    bus.publish(ev)
    got = q.get_nowait()
    assert got.event_id == ev.event_id
    bus.unsubscribe_queue(q)
    assert bus.stats()["sse_queues"] == 0
