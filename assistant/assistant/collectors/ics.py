"""ICS 日历/待办连接器：解析本地 .ics 文件（VEVENT → calendar_event，VTODO → todo）。

本地优先（ADR-0004）：只读文件，不外传；external_id 用 ICS 的 UID 保证幂等。
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from assistant.collectors.base import Collector, CollectorConfig, ConsentSpec
from assistant.errors import CollectorError
from assistant.models import RawItem


def _to_iso(value) -> str | None:
    if value is None:
        return None
    # icalendar 的 DTSTART/DUE 是 vDDDTypes 包装对象，先解包出真实 datetime/date
    dt = getattr(value, "dt", value)
    try:
        import datetime as _dt

        if isinstance(dt, _dt.datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_dt.UTC)
            return dt.astimezone(_dt.UTC).isoformat()
        if isinstance(dt, _dt.date):
            return _dt.datetime(dt.year, dt.month, dt.day, tzinfo=_dt.UTC).isoformat()
    except Exception:
        return None
    return None


class IcsCollector(Collector):
    kind = "ics"

    def __init__(self, cfg: CollectorConfig) -> None:
        super().__init__(cfg)
        paths = cfg.params.get("paths", [])
        if not paths:
            raise ValueError("ics 连接器需要 paths 参数")
        self.paths: list[Path] = [Path(p) for p in paths]

    @property
    def consent(self) -> ConsentSpec:
        return ConsentSpec(
            scope="calendar:read",
            description=f"读取本地日历/待办文件: {[str(p) for p in self.paths]}",
        )

    def collect(self) -> Iterator[RawItem]:
        from icalendar import Calendar

        for path in self.paths:
            if not path.exists():
                raise CollectorError(f"ICS 文件不存在: {path}")
            try:
                cal = Calendar.from_ical(path.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                raise CollectorError(f"ICS 解析失败: {path} ({e})") from e
            for comp in cal.walk():
                if comp.name == "VEVENT":
                    yield RawItem(
                        kind="calendar_event",
                        external_id=str(comp.get("UID", path.name)),
                        title=str(comp.get("SUMMARY", "(无标题日程)")),
                        content=str(comp.get("DESCRIPTION", "")),
                        event_time=_to_iso(comp.get("DTSTART")),
                        metadata={
                            "location": str(comp.get("LOCATION", "")),
                            "ics_file": str(path),
                        },
                    )
                elif comp.name == "VTODO":
                    yield RawItem(
                        kind="todo",
                        external_id=str(comp.get("UID", path.name)),
                        title=str(comp.get("SUMMARY", "(无标题待办)")),
                        content=str(comp.get("DESCRIPTION", "")),
                        event_time=_to_iso(comp.get("DUE")),
                        metadata={"ics_file": str(path)},
                    )


def from_settings_paths(collector_id: str, paths: list[Path]) -> IcsCollector:
    return IcsCollector(
        CollectorConfig(
            collector_id=collector_id,
            kind="ics",
            params={"paths": [str(p) for p in paths]},
        )
    )
