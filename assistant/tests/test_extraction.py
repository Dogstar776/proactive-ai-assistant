"""抽取器与仓储层测试。"""
from assistant.extraction import MockLlmExtractor, RulesExtractor
from assistant.models import ObservedEvent, RawItem


def test_rules_extractor_normalizes_and_scores():
    ex = RulesExtractor()
    raw = RawItem(
        kind="calendar_event",
        external_id="x1",
        title="  面试  ",
        content="第一段。\n\n第二段   有   多余  空白。",
        event_time=None,
    )
    out = ex.extract(raw)
    assert out.title == "面试"
    assert out.extractor == "rules"
    assert out.importance > 0  # “面试”命中紧急词
    assert "  " not in out.content


def test_rules_extractor_importance_bounded():
    ex = RulesExtractor()
    raw = RawItem(
        kind="note", external_id="x", title="t",
        content="紧急 截止 deadline 面试 汇报 逾期 asap urgent",
    )
    assert ex.extract(raw).importance <= 1.0


def test_mock_llm_extractor_is_deterministic_and_marked():
    ex = MockLlmExtractor()
    raw = RawItem(kind="note", external_id="x", title="测试标题", content="内容")
    a, b = ex.extract(raw), ex.extract(raw)
    assert a.summary == b.summary          # 确定性
    assert a.summary.startswith("[MOCK-")  # 显式 mock 标记，不伪装真实推理
    assert a.metadata["mock"] is True


def test_event_id_deterministic():
    ev1 = ObservedEvent(source="ics", source_ref="r", consent_id="c", kind="todo", title="t")
    ev2 = ObservedEvent(source="ics", source_ref="r", consent_id="c", kind="todo", title="t")
    assert ev1.event_id == ev2.event_id


def test_upsert_is_idempotent(conn):
    from assistant.memory.repository import ConsentRepository, EventRepository

    consent = ConsentRepository(conn)
    cid = consent.ensure(
        collector_id="ics", scope="calendar:read", description="t", granted_by="t"
    )
    repo = EventRepository(conn)
    ev = ObservedEvent(source="ics", source_ref="r", consent_id=cid, kind="todo", title="t")
    assert repo.upsert(ev) is True
    assert repo.upsert(ev) is False       # 重复插入被忽略
    assert repo.count() == 1
    assert repo.count_by_source() == {"ics": 1}
