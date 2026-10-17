"""仓储层：SQLite 数据访问。服务层不直接写 SQL。

幂等约定：observed_events 的 event_id 是确定性的（source|ref|内容哈希），
重复采集 → INSERT OR IGNORE → 天然幂等（种子数据可反复回放）。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from assistant.errors import NotFoundError
from assistant.logging_setup import get_logger
from assistant.models import AuditEntry, ObservedEvent

logger = get_logger("repository")


class EventRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, ev: ObservedEvent) -> bool:
        """插入事件；已存在则忽略。返回是否为新插入。"""
        row = ev.to_row()
        cur = self.conn.execute(
            """
            INSERT OR IGNORE INTO observed_events
                (event_id, source, source_ref, consent_id, kind, title, summary, content,
                 event_time, observed_at, importance, tags, extractor, provenance,
                 chain_depth, metadata)
            VALUES
                (:event_id, :source, :source_ref, :consent_id, :kind, :title, :summary, :content,
                 :event_time, :observed_at, :importance, :tags, :extractor, :provenance,
                 :chain_depth, :metadata)
            """,
            row,
        )
        self.conn.commit()
        return cur.rowcount > 0

    def list(
        self,
        *,
        source: str | None = None,
        kind: str | None = None,
        since: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ObservedEvent]:
        sql = "SELECT * FROM observed_events WHERE 1=1"
        params: list = []
        if source:
            sql += " AND source = ?"
            params.append(source)
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        if since:
            sql += " AND observed_at >= ?"
            params.append(since)
        sql += " ORDER BY observed_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        return [ObservedEvent.from_row(r) for r in self.conn.execute(sql, params)]

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM observed_events").fetchone()[0])

    def count_by_source(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT source, COUNT(*) AS n FROM observed_events GROUP BY source"
        )
        return {r["source"]: int(r["n"]) for r in rows}


class AuditRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def append(self, entry: AuditEntry) -> None:
        self.conn.execute(
            """
            INSERT INTO audit_log (audit_id, ts, action, actor, target, status, duration_ms, detail)
            VALUES (:audit_id, :ts, :action, :actor, :target, :status, :duration_ms, :detail)
            """,
            entry.to_row(),
        )
        self.conn.commit()

    def list(self, *, action: str | None = None, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM audit_log"
        params: list = []
        if action:
            sql += " WHERE action = ?"
            params.append(action)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        rows = [dict(r) for r in self.conn.execute(sql, params)]
        for r in rows:
            r["detail"] = json.loads(r.get("detail") or "{}")
        return rows


class ConsentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ensure(self, *, collector_id: str, scope: str, description: str, granted_by: str) -> str:
        """登记授权（幂等）；返回 consent_id。"""
        import uuid

        consent_id = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"{collector_id}|{scope}")
        )
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            """
            INSERT OR IGNORE INTO consent_ledger
                (consent_id, collector_id, scope, description, data_locality,
                 granted_by, granted_at, revocable)
            VALUES (?, ?, ?, ?, 'local_only', ?, ?, 1)
            """,
            (consent_id, collector_id, scope, description, granted_by, now),
        )
        self.conn.commit()
        return consent_id

    def is_granted(self, consent_id: str) -> bool:
        row = self.conn.execute(
            "SELECT revoked_at FROM consent_ledger WHERE consent_id = ?", (consent_id,)
        ).fetchone()
        if row is None:
            return False
        return row["revoked_at"] is None

    def revoke(self, consent_id: str) -> None:
        cur = self.conn.execute(
            "UPDATE consent_ledger SET revoked_at = ? WHERE consent_id = ? AND revoked_at IS NULL",
            (datetime.now(UTC).isoformat(), consent_id),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise NotFoundError(f"授权条目不存在或已撤回: {consent_id}")

    def list(self) -> list[dict]:
        return [
            dict(r)
            for r in self.conn.execute("SELECT * FROM consent_ledger ORDER BY granted_at DESC")
        ]
