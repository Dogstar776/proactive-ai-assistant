-- 002 自省报告与目标队列
-- 设计依据：论文 3.2（自省报告=目标生成的唯一内生刺激源）、3.3（统一目标队列）

CREATE TABLE IF NOT EXISTS introspection_reports (
    report_id      TEXT PRIMARY KEY,
    ts             TEXT NOT NULL,
    trigger        TEXT NOT NULL,            -- manual / api / scheduled
    gaps           TEXT NOT NULL DEFAULT '[]',   -- JSON：[{kind,title,detail,score,evidence}]
    contradictions TEXT NOT NULL DEFAULT '[]',
    audit_metrics  TEXT NOT NULL DEFAULT '{}',   -- JSON：OQ4 近似指标
    summary        TEXT NOT NULL DEFAULT '',
    extractor      TEXT NOT NULL DEFAULT 'rules',
    simulated      INTEGER NOT NULL DEFAULT 1    -- [B-simulated] 显式标记（ADR-0003）
);
CREATE INDEX IF NOT EXISTS idx_reports_ts ON introspection_reports (ts DESC);

CREATE TABLE IF NOT EXISTS goals (
    goal_id         TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    template_id     TEXT NOT NULL,             -- 模板来源（OQ7 模板移除测试的对象）
    provenance      TEXT NOT NULL DEFAULT 'template-based',
    status          TEXT NOT NULL DEFAULT 'active',  -- active/suspended/done/revoked
    priority        REAL NOT NULL DEFAULT 0,    -- 启发式 Ĝ 近似总分
    info_gain       REAL NOT NULL DEFAULT 0,    -- 认识价值项近似（缺口强度）
    practical_value REAL NOT NULL DEFAULT 0,    -- 实用价值项近似（charter 加权）
    risk_level      TEXT NOT NULL DEFAULT 'R1',
    success_criteria TEXT NOT NULL DEFAULT '',
    source_report   TEXT,
    source_gaps     TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    due_at          TEXT,
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals (status, priority DESC);

-- @down
DROP TABLE IF EXISTS goals;
DROP TABLE IF EXISTS introspection_reports;
