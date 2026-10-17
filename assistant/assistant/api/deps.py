"""依赖注入：把 Settings / DB 连接 / 服务实例装配给路由层。

连接策略：每个请求一个短连接（SQLite WAL 下足够且避免长连接占写锁）；
仓储与服务在应用启动时装配一次，挂在 app.state。
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

from assistant.config import Settings, get_settings
from assistant.db import ThreadLocalConnection
from assistant.logging_setup import get_logger
from assistant.services.observation_service import ObservationService

logger = get_logger("api.deps")

_conn_holder: ThreadLocalConnection | None = None


def get_settings_dep() -> Settings:
    return get_settings()


def shutdown_services() -> None:
    """优雅停机：关闭全部线程局部连接。"""
    global _conn_holder
    if _conn_holder is not None:
        _conn_holder.close_all()
        _conn_holder = None
    _service.cache_clear()


@lru_cache
def _service() -> ObservationService:
    global _conn_holder
    settings = get_settings()
    from assistant.collectors import KINDS, CollectorRunner
    from assistant.collectors.base import CollectorConfig
    from assistant.db import ThreadLocalConnection, migrate
    from assistant.events.bus import get_bus
    from assistant.extraction import RulesExtractor
    from assistant.memory.repository import AuditRepository, ConsentRepository, EventRepository

    migrate(settings.db_path)
    conn = ThreadLocalConnection(settings.db_path)
    _conn_holder = conn

    # 高频轻观测层默认用本地规则（ADR-0005：不调 LLM）；
    # MockLlmExtractor 保留给显式切换到 mock_llm 的场景。
    extractor = RulesExtractor()

    runner = CollectorRunner(
        events=EventRepository(conn),
        audit=AuditRepository(conn),
        consent=ConsentRepository(conn),
        bus=get_bus(),
        extractor=extractor,
        granted_by=settings.consent_granted_by,
    )
    # 按配置注册连接器（本地优先：ICS/笔记/RSS 均可为本地路径）
    for i, p in enumerate(settings.ics_paths):
        runner.register_config(
            CollectorConfig(collector_id=f"ics:{i}:{p}", kind="ics",
                            params={"paths": [str(p)]}),
            KINDS["ics"],
        )
    for i, p in enumerate(settings.notes_paths):
        runner.register_config(
            CollectorConfig(collector_id=f"notes:{i}:{p}", kind="markdown_notes",
                            params={"paths": [str(p)]}),
            KINDS["markdown_notes"],
        )
    if settings.rss_urls:
        runner.register_config(
            CollectorConfig(collector_id="rss:default", kind="rss",
                            params={"urls": settings.rss_urls}),
            KINDS["rss"],
        )

    # 未配置任何采集源时，挂载 fixtures 演示连接器（开箱即用；明确标注为演示数据，
    # 与用户真实数据隔离——collector_id 带 fixture: 前缀，仪表盘可区分）。
    if not runner.list_collectors():
        fixtures = Path(__file__).resolve().parent.parent.parent / "fixtures"
        demo = [
            (fixtures / "sample_calendar.ics", "ics"),
            (fixtures / "notes", "markdown_notes"),
            (fixtures / "feed.xml", "rss"),
        ]
        for path, kind in demo:
            if not path.exists():
                continue
            params = (
                {"paths": [str(path)]} if kind != "rss" else {"urls": [str(path)]}
            )
            runner.register_config(
                CollectorConfig(collector_id=f"fixture:{kind}", kind=kind, params=params),
                KINDS[kind],
            )
        if runner.list_collectors():
            logger.warning(
                "collectors.defaulted_to_fixtures: 未配置采集源，已挂载 fixtures 演示连接器"
                "（非用户真实数据）；在 .env 中设置 COLLECTOR_* 后重启即可接入自己的数据"
            )
    return ObservationService(
        runner=runner,
        events=EventRepository(conn),
        audit=AuditRepository(conn),
        consent=ConsentRepository(conn),
        bus=get_bus(),
    )


def get_observation_service() -> ObservationService:
    return _service()


def fresh_connection() -> sqlite3.Connection:
    """仅供脚本/测试使用的一次性连接。"""
    from assistant.db import connect

    return connect(get_settings().db_path)
