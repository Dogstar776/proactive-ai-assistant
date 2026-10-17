"""pytest 公共 fixtures：临时库 + 测试专用 Settings。"""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("COLLECTOR_ICS_PATHS", str(FIXTURES / "sample_calendar.ics"))
    monkeypatch.setenv("COLLECTOR_NOTES_PATHS", str(FIXTURES / "notes"))
    monkeypatch.setenv("COLLECTOR_RSS_URLS", str(FIXTURES / "feed.xml"))
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    from assistant.config import reset_settings_cache

    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture
def settings():
    from assistant.config import get_settings

    return get_settings()


@pytest.fixture
def conn(settings):
    from assistant.db import connect, migrate

    migrate(settings.db_path)
    c = connect(settings.db_path)
    yield c
    c.close()


@pytest.fixture
def runner(conn):
    from assistant.collectors import CollectorRunner
    from assistant.events.bus import EventBus
    from assistant.extraction import RulesExtractor
    from assistant.memory.repository import AuditRepository, ConsentRepository, EventRepository

    return CollectorRunner(
        events=EventRepository(conn),
        audit=AuditRepository(conn),
        consent=ConsentRepository(conn),
        bus=EventBus(),
        extractor=RulesExtractor(),
    )


@pytest.fixture
def client(settings):
    from fastapi.testclient import TestClient

    from assistant.api.app import create_app
    from assistant.api.deps import _service

    _service.cache_clear()
    app = create_app(settings)
    with TestClient(app) as c:
        yield c
    _service.cache_clear()
