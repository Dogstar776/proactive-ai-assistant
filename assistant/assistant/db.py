"""SQLite 连接管理与迁移执行。

- WAL 模式 + 外键约束；连接池对单文件 SQLite 的意义由 Repository 层的
  短事务 + 上下文管理器承担（避免长连接占用写锁）。
- 迁移文件可回滚：每个 .sql 内含 `-- @down` 分隔的上/下两段；
  已应用的迁移记录 checksum，运行时发现被篡改即快速失败。
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path

from assistant.errors import ConfigurationError
from assistant.logging_setup import get_logger, log_event

logger = get_logger("db")

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


class ThreadLocalConnection:
    """线程局部 SQLite 连接（鸭子类型兼容 sqlite3.Connection 的 execute/commit）。

    存在原因：FastAPI 的同步端点在 anyio 线程池执行、SSE 生成器在事件循环线程
    执行，单一共享连接会触发 "SQLite objects created in a thread can only be
    used in that same thread"。每个工作线程一个连接，WAL 模式下读写互不阻塞。
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._local = threading.local()
        self._all: list[sqlite3.Connection] = []
        self._lock = threading.Lock()

    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = connect(self._path)
            self._local.conn = c
            with self._lock:
                self._all.append(c)
        return c

    # ── 鸭子类型：仓库层只用到这两个方法 ──
    def execute(self, *args, **kwargs):
        return self._conn().execute(*args, **kwargs)

    def commit(self) -> None:
        self._conn().commit()

    def close_all(self) -> None:
        with self._lock:
            for c in self._all:
                with suppress(sqlite3.Error):
                    c.close()
            self._all.clear()


@contextmanager
def transaction(conn: sqlite3.Connection):
    """多步写入的事务上下文；异常即回滚。"""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _split_migration(text: str) -> tuple[str, str | None]:
    up, _, down = text.partition("-- @down")
    return up.strip(), (down.strip() or None)


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _ensure_meta(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            checksum    TEXT NOT NULL,
            applied_at  TEXT NOT NULL
        )
        """
    )
    conn.commit()


def migrate(db_path: Path, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """应用全部待执行迁移，返回本次应用的版本名列表。"""
    conn = connect(db_path)
    try:
        _ensure_meta(conn)
        applied = {r["version"]: r["checksum"] for r in conn.execute(
            "SELECT version, checksum FROM schema_migrations"
        )}
        done: list[str] = []
        files = sorted(migrations_dir.glob("*.sql"))
        if not files:
            raise ConfigurationError(f"迁移目录为空: {migrations_dir}")
        for f in files:
            version = int(f.name.split("_", 1)[0])
            text = f.read_text(encoding="utf-8")
            chk = _checksum(text)
            if version in applied:
                if applied[version] != chk:
                    raise ConfigurationError(
                        f"迁移 {f.name} 应用后内容被篡改（checksum 不符），拒绝启动"
                    )
                continue
            up, _ = _split_migration(text)
            with transaction(conn):
                conn.executescript(up)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, checksum, applied_at)"
                    " VALUES (?, ?, ?, ?)",
                    (version, f.name, chk, datetime.now(UTC).isoformat()),
                )
            done.append(f.name)
            log_event(logger, 20, "migration.applied", version=version, name=f.name)
        return done
    finally:
        conn.close()


def rollback_last(db_path: Path, migrations_dir: Path = MIGRATIONS_DIR) -> str | None:
    """回滚最后一个已应用迁移（开发/应急用；幂等）。"""
    conn = connect(db_path)
    try:
        _ensure_meta(conn)
        row = conn.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        f = migrations_dir / row["name"]
        _, down = _split_migration(f.read_text(encoding="utf-8"))
        if not down:
            raise ConfigurationError(f"迁移 {row['name']} 未提供 @down 段，无法回滚")
        with transaction(conn):
            conn.executescript(down)
            conn.execute("DELETE FROM schema_migrations WHERE version = ?", (row["version"],))
        log_event(logger, 30, "migration.rolled_back", version=row["version"], name=row["name"])
        return row["name"]
    finally:
        conn.close()
