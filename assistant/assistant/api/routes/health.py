"""路由层：健康检查。"""
from fastapi import APIRouter

from assistant.api.deps import get_settings_dep
from assistant.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready(settings: Settings = get_settings_dep()) -> dict:
    """就绪检查：数据目录可写 + 迁移已应用。"""
    from assistant.db import connect, migrate

    try:
        migrate(settings.db_path)
        conn = connect(settings.db_path)
        version = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()["v"]
        conn.close()
        return {"status": "ready", "db": str(settings.db_path), "schema_version": version}
    except Exception as e:  # noqa: BLE001 — 就绪检查需要兜底
        return {"status": "not_ready", "error": str(e)}
