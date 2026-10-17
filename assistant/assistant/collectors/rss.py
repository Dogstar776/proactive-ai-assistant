"""RSS/信息流连接器：feedparser 解析本地文件或远程 URL。

P2 默认用本地 fixture 文件（离线可复现）；远程 URL 需在配置中显式声明。
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from assistant.collectors.base import Collector, CollectorConfig, ConsentSpec
from assistant.errors import CollectorError
from assistant.models import RawItem


class RssCollector(Collector):
    kind = "rss"

    def __init__(self, cfg: CollectorConfig) -> None:
        super().__init__(cfg)
        self.feeds: list[str] = [str(u) for u in cfg.params.get("urls", [])]
        if not self.feeds:
            raise ValueError("rss 连接器需要 urls 参数")

    @property
    def consent(self) -> ConsentSpec:
        return ConsentSpec(
            scope="feed:read",
            description=f"读取信息流: {self.feeds}",
        )

    def collect(self) -> Iterator[RawItem]:
        import feedparser

        for feed in self.feeds:
            source = Path(feed)
            parsed = (
                feedparser.parse(str(source))
                if source.exists()
                else feedparser.parse(feed)
            )
            if parsed.bozo and not parsed.entries:
                raise CollectorError(f"RSS 解析失败: {feed}")
            for entry in parsed.entries:
                yield RawItem(
                    kind="feed_item",
                    external_id=str(entry.get("id") or entry.get("link") or entry.get("title")),
                    title=str(entry.get("title", "(无标题)")),
                    content=str(entry.get("summary", "")),
                    event_time=None,
                    metadata={
                        "feed": feed,
                        "link": str(entry.get("link", "")),
                        "published": str(entry.get("published", "")),
                    },
                )
