"""Markdown 笔记文件夹连接器。

每个 .md 文件产出一条 note 事件；文件内的 `- [ ]` 待办单独产出一条 todo 事件
（external_id = 相对路径 + 行号，保证重复采集幂等）。
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from assistant.collectors.base import Collector, CollectorConfig, ConsentSpec
from assistant.errors import CollectorError
from assistant.models import RawItem

_TODO_RE = re.compile(r"^\s*-\s*\[ \]\s*(.+)$")
_HEADING_RE = re.compile(r"^#\s+(.+)$")


def _truncate(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n…[截断]"


class MarkdownNotesCollector(Collector):
    kind = "markdown_notes"

    def __init__(self, cfg: CollectorConfig) -> None:
        super().__init__(cfg)
        paths = cfg.params.get("paths", [])
        if not paths:
            raise ValueError("markdown_notes 连接器需要 paths 参数")
        self.paths: list[Path] = [Path(p) for p in paths]

    @property
    def consent(self) -> ConsentSpec:
        return ConsentSpec(
            scope="notes:read",
            description=f"读取本地 Markdown 笔记目录: {[str(p) for p in self.paths]}",
        )

    def collect(self) -> Iterator[RawItem]:
        for root in self.paths:
            if not root.exists():
                raise CollectorError(f"笔记目录不存在: {root}")
            for md in sorted(root.rglob("*.md")):
                if any(part.startswith(".") for part in md.parts):
                    continue
                text = md.read_text(encoding="utf-8", errors="replace")
                rel = str(md)
                heading = next(
                    (
                        m.group(1).strip()
                        for ln in text.splitlines()
                        if (m := _HEADING_RE.match(ln))
                    ),
                    md.stem,
                )
                yield RawItem(
                    kind="note",
                    external_id=f"note:{rel}",
                    title=heading,
                    content=_truncate(text),
                    metadata={"path": rel, "bytes": md.stat().st_size},
                )
                for lineno, line in enumerate(text.splitlines(), 1):
                    m = _TODO_RE.match(line)
                    if m:
                        yield RawItem(
                            kind="todo",
                            external_id=f"todo:{rel}:{lineno}",
                            title=m.group(1).strip(),
                            content="",
                            metadata={"path": rel, "line": lineno},
                        )
