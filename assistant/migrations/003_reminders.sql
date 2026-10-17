-- 003 提醒（干预）台账
-- 设计依据：论文 3.5（全量决策日志支持事后审计，"沉默"同样留痕）

CREATE TABLE IF NOT EXISTS reminders (
    reminder_id     TEXT PRIMARY KEY,
    goal_id         TEXT,                   -- 派生自哪个目标（可空：系统级提醒）
    kind            TEXT NOT NULL,          -- deadline_nudge / theme_digest / cleanup_list
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    risk_level      TEXT NOT NULL,          -- R0..R3（门控输入）
    state           TEXT NOT NULL,          -- silence / act / assist / ask（四态判决）
    status          TEXT NOT NULL,          -- delivered / pending / suppressed / approved / rejected / expired
    decision_reason TEXT NOT NULL DEFAULT '', -- 沉默/挂起的原因（可审计的关键）
    cooldown_key    TEXT NOT NULL,          -- 同键在冷却期内不重复生成
    channel         TEXT NOT NULL DEFAULT 'sse',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    expires_at      TEXT,                   -- ask/assist 的超时（超时默认拒绝，论文 3.5）
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reminders_goal ON reminders (goal_id);

-- @down
DROP TABLE IF EXISTS reminders;
