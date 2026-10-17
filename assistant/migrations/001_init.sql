-- 001 初始化：观测事件 / 记忆 / 审计日志 / 授权账本
-- 设计依据：论文 3.1（观测层输出增量事件）、3.5（全量决策日志）、ADR-0004（consent ledger + provenance）

CREATE TABLE IF NOT EXISTS observed_events (
    event_id      TEXT PRIMARY KEY,          -- uuid5(source|source_ref|external_id)，幂等
    source        TEXT NOT NULL,             -- ics_calendar / markdown_notes / rss_feed / internal_probe
    source_ref    TEXT NOT NULL,             -- 连接器配置 ID（文件路径/URL）
    consent_id    TEXT NOT NULL,             -- 关联授权账本条目
    kind          TEXT NOT NULL,             -- calendar_event / todo / note / feed_item
    title         TEXT NOT NULL,
    summary       TEXT NOT NULL DEFAULT '',
    content       TEXT NOT NULL DEFAULT '',
    event_time    TEXT,                      -- ISO8601，事件发生/计划时间（可空）
    observed_at   TEXT NOT NULL,             -- ISO8601，采集时间
    importance    REAL NOT NULL DEFAULT 0,   -- 0~1，规则/抽取器给出的重要度提示
    tags          TEXT NOT NULL DEFAULT '[]', -- JSON 数组
    extractor     TEXT NOT NULL DEFAULT 'rules', -- rules / mock_llm / llm
    provenance    TEXT NOT NULL,             -- user_injected / system_derived / external_retrieved
    chain_depth   INTEGER NOT NULL DEFAULT 0,-- 生成链深度（OQ4：0=原始经验）
    metadata      TEXT NOT NULL DEFAULT '{}', -- JSON：源特定字段
    FOREIGN KEY (consent_id) REFERENCES consent_ledger (consent_id)
);
CREATE INDEX IF NOT EXISTS idx_events_observed_at ON observed_events (observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_source ON observed_events (source, source_ref);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_idem ON observed_events (source, source_ref, kind, title);

CREATE TABLE IF NOT EXISTS memories (
    memory_id     TEXT PRIMARY KEY,
    content       TEXT NOT NULL,
    provenance    TEXT NOT NULL,             -- user_injected / system_derived / external_retrieved
    chain_depth   INTEGER NOT NULL DEFAULT 0,
    confidence    REAL NOT NULL DEFAULT 1.0, -- 置信度（随时间衰减的起点）
    source_event  TEXT,                      -- 派生自哪条观测事件
    created_at    TEXT NOT NULL,
    last_used_at  TEXT,
    use_count     INTEGER NOT NULL DEFAULT 0,
    metadata      TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories (created_at DESC);

CREATE TABLE IF NOT EXISTS consent_ledger (
    consent_id    TEXT PRIMARY KEY,          -- uuid5(collector_id|scope)
    collector_id  TEXT NOT NULL,
    scope         TEXT NOT NULL,             -- 如 calendar:read
    description   TEXT NOT NULL,
    data_locality TEXT NOT NULL DEFAULT 'local_only',
    granted_by    TEXT NOT NULL,
    granted_at    TEXT NOT NULL,
    revoked_at    TEXT,                      -- 非空即已撤回
    revocable     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id      TEXT PRIMARY KEY,
    ts            TEXT NOT NULL,
    action        TEXT NOT NULL,             -- collector.run / consent.revoke / gate.decision ...
    actor         TEXT NOT NULL,             -- collector:ics_calendar / system / owner
    target        TEXT,
    status        TEXT NOT NULL,             -- ok / skipped / error
    duration_ms   INTEGER,
    detail        TEXT NOT NULL DEFAULT '{}' -- JSON：计数、错误、请求 ID 等
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log (ts DESC);

-- @down
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS consent_ledger;
DROP TABLE IF EXISTS memories;
DROP TABLE IF EXISTS observed_events;
