import { useCallback, useEffect, useState } from "react";
import { api, type ObservedEvent } from "../api/client";
import LoopRing from "../components/LoopRing";
import { Badge, Empty, GlassCard, SectionTitle, Stat, fmtTime } from "../components";

export default function LoopView({ live }: { live: ObservedEvent[] }) {
  const [stats, setStats] = useState<{ total: number; by_source: Record<string, number> }>({
    total: 0,
    by_source: {},
  });
  const [goals, setGoals] = useState<Record<string, number>>({});
  const [reminders, setReminders] = useState<{ act: number; silence: number; ask: number }>({
    act: 0,
    silence: 0,
    ask: 0,
  });
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, g, r] = await Promise.all([api.stats(), api.goals(), api.reminders()]);
      setStats(s);
      setGoals(g.stats.by_status);
      const act = r.items.filter((x) => x.state === "act").length;
      const silence = r.items.filter((x) => x.state === "silence").length;
      const ask = r.items.filter((x) => x.state === "ask").length;
      setReminders({ act, silence, ask });
    } catch {
      /* 离线时保留上次数据 */
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, live.length]);

  const run = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key);
    try {
      await fn();
    } finally {
      setBusy(key);
      setTimeout(() => setBusy(null), 600);
      void refresh();
    }
  };

  const center = (
    <>
      <text x={160} y={148} textAnchor="middle" fontSize="11" fontWeight="600" fill="rgba(60,60,67,0.5)">
        观测事件
      </text>
      <text x={160} y={178} textAnchor="middle" fontSize="34" fontWeight="700" fill="#1d1d1f">
        {stats.total}
      </text>
      <text x={160} y={196} textAnchor="middle" fontSize="10.5" fill="rgba(60,60,67,0.45)">
        活跃目标 {goals.active ?? 0} · 待确认 {reminders.ask}
      </text>
    </>
  );

  return (
    <>
      <SectionTitle>持续认知闭环 · 实时</SectionTitle>
      <div className="loop-wrap">
        <GlassCard className="loop-stage">
          <LoopRing live={live} center={center} />
        </GlassCard>

        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          <div className="stat-grid">
            <Stat label="今日触达" value={reminders.act} tone="ok" />
            <Stat label="主动沉默" value={reminders.silence} tone="neutral" />
            <Stat label="挂起请示" value={reminders.ask} tone="warn" />
            <Stat label="活跃目标" value={goals.active ?? 0} tone="accent" />
          </div>

          <GlassCard style={{ padding: 18 }}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
              <button
                className="btn primary"
                disabled={busy !== null}
                onClick={() => void run("collect", () => api.runCollectors())}
              >
                {busy === "collect" ? "采集中…" : "① 轻观测周期"}
              </button>
              <button
                className="btn"
                disabled={busy !== null}
                onClick={() => void run("deep", () => api.runDeepCycle())}
              >
                {busy === "deep" ? "自省中…" : "② 深周期（自省→目标）"}
              </button>
              <button
                className="btn"
                disabled={busy !== null}
                onClick={() => void run("remind", () => api.runReminders())}
              >
                {busy === "remind" ? "门控中…" : "③ 提醒周期（四态门控）"}
              </button>
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.7 }}>
              三个按钮对应论文的三类认知周期：高频轻观测（本地规则，不调 LLM）→
              低频深周期（自省报告 + 模板化目标合成，[B-simulated]）→
              门控判决（沉默/询问/协助/行动，全部留痕）。
            </div>
          </GlassCard>

          <GlassCard style={{ padding: 18 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-2)" }}>实时事件流</span>
              <span className="pulse" />
            </div>
            <div className="ticker">
              {live.length === 0 && <Empty>等待事件…（SSE 已连接，触发上方周期即可看到流动）</Empty>}
              {live.map((ev) => (
                <div className="ticker-item" key={ev.event_id}>
                  <span className="t num">{fmtTime(ev.observed_at)}</span>
                  <Badge tone="accent">{ev.source}</Badge>
                  <span
                    style={{
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {ev.title}
                  </span>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </>
  );
}
