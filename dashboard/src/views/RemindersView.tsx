import { useCallback, useEffect, useState } from "react";
import { api, type Reminder } from "../api/client";
import { Badge, Empty, GlassCard, SectionTitle, Stat, fmtTime } from "../components";

const STATE_TONE: Record<string, "ok" | "warn" | "danger" | "neutral" | "accent"> = {
  act: "ok",
  assist: "warn",
  ask: "danger",
  silence: "neutral",
};

const STATE_LABEL: Record<string, string> = {
  act: "行动",
  assist: "协助",
  ask: "询问",
  silence: "沉默",
};

export default function RemindersView() {
  const [items, setItems] = useState<Reminder[]>([]);
  const [fatigue, setFatigue] = useState<{ ask_total: number; approval_rate: number | null }>({
    ask_total: 0,
    approval_rate: null,
  });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [r, f] = await Promise.all([api.reminders(), api.fatigue()]);
      setItems(r.items);
      setFatigue(f);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const pending = items.filter((i) => i.status === "pending");
  const others = items.filter((i) => i.status !== "pending");

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const batch = async (action: "approve" | "reject") => {
    if (!selected.size) return;
    await api.batch([...selected], action);
    setSelected(new Set());
    void refresh();
  };

  return (
    <>
      <SectionTitle>提醒与门控 · L5（沉默-询问-协助-行动）</SectionTitle>
      <div className="stat-grid" style={{ marginBottom: 14 }}>
        <Stat label="待确认" value={pending.length} tone="warn" />
        <Stat label="7 日请示" value={fatigue.ask_total} />
        <Stat
          label="批准率"
          value={fatigue.approval_rate === null ? "—" : (fatigue.approval_rate * 100).toFixed(0)}
          unit={fatigue.approval_rate === null ? undefined : "%"}
          tone={fatigue.approval_rate !== null && fatigue.approval_rate < 0.3 ? "danger" : "ok"}
        />
        <Stat label="本轮沉默" value={items.filter((i) => i.state === "silence").length} tone="neutral" />
      </div>

      <SectionTitle>待确认队列（人类在场时批量审计）</SectionTitle>
      <GlassCard style={{ padding: 14, marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: pending.length ? 12 : 0, alignItems: "center" }}>
          <button className="btn small ok" disabled={!selected.size} onClick={() => void batch("approve")}>
            批量批准（{selected.size}）
          </button>
          <button className="btn small danger" disabled={!selected.size} onClick={() => void batch("reject")}>
            批量拒绝（{selected.size}）
          </button>
          <span style={{ flex: 1 }} />
          <button className="btn small" onClick={() => void refresh()}>
            刷新
          </button>
        </div>
        {loading && <Empty>加载中…</Empty>}
        {!loading && pending.length === 0 && <Empty>无待确认项——该沉默时沉默，也是一种输出</Empty>}
        {pending.map((r) => (
          <div className="row row-enter" key={r.reminder_id}>
            <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={selected.has(r.reminder_id)}
                onChange={() => toggle(r.reminder_id)}
                style={{ width: 17, height: 17, accentColor: "var(--accent)" }}
              />
            </label>
            <div className="row-main">
              <div className="row-title">{r.title}</div>
              <div className="row-sub">{r.body.slice(0, 110)}…</div>
            </div>
            <div className="row-side">
              <Badge tone={STATE_TONE[r.state]}>{STATE_LABEL[r.state]}</Badge>
              <Badge tone={r.risk_level === "R3" ? "danger" : "warn"}>{r.risk_level}</Badge>
              <button className="btn small ok" onClick={() => void api.approve(r.reminder_id).then(refresh)}>
                批准
              </button>
              <button className="btn small danger" onClick={() => void api.reject(r.reminder_id).then(refresh)}>
                拒绝
              </button>
            </div>
          </div>
        ))}
      </GlassCard>

      <SectionTitle>干预台账（含被沉默的——可审计的沉默）</SectionTitle>
      <GlassCard style={{ padding: 8 }}>
        {!loading && others.length === 0 && <Empty>暂无记录</Empty>}
        {others.map((r) => (
          <div className="row" key={r.reminder_id}>
            <div className="row-main">
              <div className="row-title" style={{ fontSize: 13.5 }}>{r.title}</div>
              <div className="row-sub">
                {r.status === "suppressed" ? `沉默原因：${r.decision_reason}` : r.decision_reason}
              </div>
            </div>
            <div className="row-side">
              <Badge tone={STATE_TONE[r.state]}>{STATE_LABEL[r.state]}</Badge>
              <Badge
                tone={
                  r.status === "delivered"
                    ? "ok"
                    : r.status === "suppressed"
                      ? "neutral"
                      : r.status === "expired"
                        ? "warn"
                        : "danger"
                }
              >
                {r.status}
              </Badge>
              <span className="num" style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                {fmtTime(r.created_at)}
              </span>
            </div>
          </div>
        ))}
      </GlassCard>
    </>
  );
}
