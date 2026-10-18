"""API Key 鉴权测试（移动端接管入口）。"""
from assistant.config import Settings


def _settings(**kw) -> Settings:
    base = dict(api_host="127.0.0.1", api_port=8799, data_dir=__import__("pathlib").Path(
        __import__("tempfile").mkdtemp()), log_level="ERROR")
    base.update(kw)
    return Settings(**base)


def test_api_key_required_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "d"))
    monkeypatch.setenv("API_KEY", "secret-key-123")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    from assistant.config import reset_settings_cache

    reset_settings_cache()
    from fastapi.testclient import TestClient

    from assistant.api.app import create_app

    with TestClient(create_app()) as c:
        # /health 开放
        assert c.get("/health").status_code == 200
        # /api/* 无 key → 401
        r = c.get("/api/v1/events")
        assert r.status_code == 401
        assert r.json()["code"] == "unauthorized"
        # 带 key → 放行
        ok = c.get("/api/v1/events", headers={"X-API-Key": "secret-key-123"})
        assert ok.status_code == 200
        # 错 key → 401
        bad = c.get("/api/v1/events", headers={"X-API-Key": "wrong"})
        assert bad.status_code == 401
    reset_settings_cache()


def test_no_key_means_open(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "d"))
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    from assistant.config import reset_settings_cache

    reset_settings_cache()
    from fastapi.testclient import TestClient

    from assistant.api.app import create_app

    with TestClient(create_app()) as c:
        assert c.get("/api/v1/events").status_code == 200
    reset_settings_cache()
