import { useEffect, useState } from "react";
import { api, type IntrospectionReport } from "../api/client";
import { Badge, Empty, GlassCard, SectionTitle, Stat } from "../components";

export default function IntrospectionView() {
  const [reports, setReports] = useState<IntrospectionReport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .reports()
      .then((d) => setReports(d.items))
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  }, []);

  const latest = reports[0];

  return (
    <>
      <SectionTitle>自省报告 · L2 [B-simulated]</SectionTitle>
      {loading && <GlassCard style={{ padding: 20 }}><Empty>加载中…</Empty></GlassCard>}
      {!loading && !latest && (
        <GlassCard style={{ padding: 20 }}>
          <Empty>暂无报告——到「认知环」跑一次深周期</Empty>
        </GlassCard>
      )}
      {latest && (
        <>
          <GlassCard style={{ padding: 20, marginBottom: 14 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12, flexWrap: "wrap" }}>
              <Badge tone="accent">{latest.trigger}</Badge>
              <span className="num" style={{ fontSize: 12, color: "var(--text-3)" }}>
                {latest.ts.replace("T", " ").slice(0, 16)}
              </span>
              <span style={{ flex: 1 }} />
              <Badge tone="neutral">[B-simulated] 规则自省，非可靠元认知</Badge>
            </div>
            <div style={{ fontSize: 14.5, fontWeight: 600, lineHeight: 1.6 }}>{latest.summary}</div>
          </GlassCard>

          <div className="stat-grid" style={{ marginBottom: 14 }}>
            <Stat label="自生内容占比" value={(latest.audit_metrics.system_derived_ratio * 100).toFixed(1)} unit="%" />
            <Stat label="跨源重复率" value={(latest.audit_metrics.duplicate_ratio * 100).toFixed(1)} unit="%" />
            <Stat label="过期未消" value={latest.audit_metrics.overdue_open} />
            <Stat label="最大生成链" value={latest.audit_metrics.max_chain_depth} />
          </div>

          <SectionTitle>缺口清单（目标生成的唯一内生刺激源）</SectionTitle>
          <GlassCard style={{ padding: 8 }}>
            {latest.gaps.length === 0 && <Empty>未检测到缺口</Empty>}
            {latest.gaps.map((g, i) => (
              <div className="row row-enter" key={`${g.kind}-${i}`}>
                <div className="row-main">
                  <div className="row-title">{g.title}</div>
                  <div className="row-sub">{g.detail}</div>
                </div>
                <div className="row-side">
                  <Badge tone={g.kind === "deadline-prep" ? "danger" : g.kind === "contradiction" ? "warn" : "accent"}>
                    {g.kind}
                  </Badge>
                  <div className="prio">
                    <span style={{ transform: `scaleX(${Math.min(g.score, 1)})` }} />
                  </div>
                  <span className="num" style={{ fontSize: 12, width: 38, textAlign: "right" }}>
                    {g.score.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </GlassCard>

          {reports.length > 1 && (
            <>
              <SectionTitle>历史报告（{reports.length}）</SectionTitle>
              <GlassCard style={{ padding: 8 }}>
                {reports.slice(1).map((r) => (
                  <div className="row" key={r.report_id}>
                    <div className="row-main">
                      <div className="row-title" style={{ fontSize: 13, color: "var(--text-2)" }}>
                        {r.summary.slice(0, 72)}…
                      </div>
                    </div>
                    <span className="num" style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                      {r.ts.replace("T", " ").slice(0, 16)}
                    </span>
                  </div>
                ))}
              </GlassCard>
            </>
          )}
        </>
      )}
    </>
  );
}
