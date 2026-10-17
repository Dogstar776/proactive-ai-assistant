"""采集器包。"""
from assistant.collectors.base import Collector, CollectorConfig, ConsentSpec
from assistant.collectors.ics import IcsCollector
from assistant.collectors.markdown_notes import MarkdownNotesCollector
from assistant.collectors.rss import RssCollector
from assistant.collectors.runner import CollectorResult, CollectorRunner

KINDS: dict[str, type[Collector]] = {
    "ics": IcsCollector,
    "markdown_notes": MarkdownNotesCollector,
    "rss": RssCollector,
}

__all__ = [
    "Collector", "CollectorConfig", "ConsentSpec", "CollectorRunner", "CollectorResult",
    "IcsCollector", "MarkdownNotesCollector", "RssCollector", "KINDS",
]
