"""采集器测试：ICS / Markdown / RSS。"""
from pathlib import Path

from assistant.collectors import IcsCollector, MarkdownNotesCollector, RssCollector
from assistant.collectors.base import CollectorConfig

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_ics_collector_parses_events_and_todos():
    c = IcsCollector(CollectorConfig(
        collector_id="ics:t", kind="ics",
        params={"paths": [str(FIXTURES / "sample_calendar.ics")]},
    ))
    items = list(c.collect())
    kinds = {i.kind for i in items}
    assert kinds == {"calendar_event", "todo"}
    assert any("视频面试" in i.title for i in items)
    assert all(i.external_id for i in items)
    # DTSTART/DUE 必须解包为 ISO 时间（重要度评分与 P3 依赖它）
    interview = next(i for i in items if "视频面试" in i.title)
    assert interview.event_time is not None
    assert interview.event_time.startswith("2026-10-21")
    todo = next(i for i in items if i.kind == "todo")
    assert todo.event_time is not None
    assert c.consent.scope == "calendar:read"


def test_ics_missing_file_raises_collector_error():
    from assistant.errors import CollectorError

    c = IcsCollector(CollectorConfig(
        collector_id="ics:missing", kind="ics", params={"paths": ["/nope/x.ics"]}
    ))
    try:
        list(c.collect())
        raise AssertionError("应当抛 CollectorError")
    except CollectorError:
        pass


def test_markdown_collector_extracts_notes_and_todos():
    c = MarkdownNotesCollector(CollectorConfig(
        collector_id="notes:t", kind="markdown_notes",
        params={"paths": [str(FIXTURES / "notes")]},
    ))
    items = list(c.collect())
    notes = [i for i in items if i.kind == "note"]
    todos = [i for i in items if i.kind == "todo"]
    assert len(notes) == 2
    assert len(todos) >= 5
    assert any("面试" in t.title for t in todos)
    # 幂等键稳定
    ids = [i.external_id for i in items]
    assert len(ids) == len(set(ids))


def test_rss_collector_reads_local_feed():
    c = RssCollector(CollectorConfig(
        collector_id="rss:t", kind="rss", params={"urls": [str(FIXTURES / "feed.xml")]},
    ))
    items = list(c.collect())
    assert len(items) == 3
    assert all(i.kind == "feed_item" for i in items)
