import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Badge, Empty, GlassCard, SectionTitle, Stat } from "../components";

export default function CostsView() {
  const [status, setStatus] = useState<{
    provider: string;
    model: string;
    deep_cycles_per_day: number;
    daily_token_budget: number;
    data_dir: string;
  } | null>(null);
  const [audit, setAudit] = useState<{ action: string; status: string; target: string }[]>([]);
  const [consents, setConsents] = useState<{ scope: string; revoked_at: string | null }[]>([]);

  useEffect(() => {
    api.systemStatus().then(setStatus).catch(() => setStatus(null));
    api.audit().then((d) => setAudit(d.items)).catch(() => setAudit([]));
    api.consents().then((d) => setConsents(d.items)).catch(() => setConsents([]));
  }, []);

  const cycleCount = (action: string) => audit.filter((a) => a.action === action).length;

  return (
    <>
      <SectionTitle>运行与成本 · ADR-0005</SectionTitle>
      <div className="stat-grid" style={{ marginBottom: 14 }}>
        <Stat label="Provider" value={status?.provider ?? "—"} tone={status?.provider === "mock" ? "neutral" : "accent"} />
        <Stat label="深周期/日" value={status?.deep_cycles_per_day ?? "—"} />
        <Stat label="日 Token 预算" value={status?.daily_token_budget ?? "—"} />
        <Stat label="Mock 模式推理成本" value="¥0" tone="ok" />
      </div>

      <SectionTitle>周期计数（审计日志聚合）</SectionTitle>
      <GlassCard style={{ padding: 8, marginBottom: 14 }}>
        {[
          { action: "collector.run", label: "轻观测周期（本地规则，零成本）" },
          { action: "gate.decision", label: "门控判决（含沉默，全部留痕）" },
          { action: "consent.revoke", label: "授权撤回" },
          { action: "reminder.expired", label: "超时默认拒绝" },
        ].map((row) => (
          <div className="row" key={row.action}>
            <div className="row-main">
              <div className="row-title" style={{ fontSize: 13.5 }}>
                {row.label}
              </div>
              <div className="row-sub num">{row.action}</div>
            </div>
            <span className="num" style={{ fontSize: 18, fontWeight: 700 }}>
              {cycleCount(row.action)}
            </span>
          </div>
        ))}
        {audit.length === 0 && <Empty>暂无审计记录</Empty>}
      </GlassCard>

      <SectionTitle>授权账本（consent ledger）</SectionTitle>
      <GlassCard style={{ padding: 8 }}>
        {consents.length === 0 && <Empty>暂无授权条目</Empty>}
        {consents.map((c, i) => (
          <div className="row" key={i}>
            <div className="row-main">
              <div className="row-title" style={{ fontSize: 13.5 }}>
                {c.scope}
              </div>
              <div className="row-sub">本地优先 · 可撤回</div>
            </div>
            <Badge tone={c.revoked_at ? "danger" : "ok"}>{c.revoked_at ? "已撤回" : "生效中"}</Badge>
          </div>
        ))}
      </GlassCard>

      <SectionTitle>数据位置</SectionTitle>
      <GlassCard style={{ padding: 18 }}>
        <div className="num" style={{ fontSize: 13, color: "var(--text-2)" }}>
          {status?.data_dir ?? "—"}（SQLite + 向量库，gitignored，永不入仓库）
        </div>
      </GlassCard>
    </>
  );
}
