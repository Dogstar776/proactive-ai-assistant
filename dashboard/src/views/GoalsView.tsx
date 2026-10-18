import { useCallback, useEffect, useState } from "react";
import { api, type Goal } from "../api/client";
import { Badge, Empty, GlassCard, SectionTitle } from "../components";

const TEMPLATE_LABEL: Record<string, string> = {
  "deadline-prep": "截止准备",
  "theme-cluster": "主题聚类",
  "contradiction-scan": "矛盾清理",
};

export default function GoalsView() {
  const [items, setItems] = useState<Goal[]>([]);
  const [byStatus, setByStatus] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const d = await api.goals();
      setItems(d.items);
      setByStatus(d.stats.by_status);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const act = async (id: string, status: string) => {
    await api.setGoalStatus(id, status);
    void refresh();
  };

  return (
    <>
      <SectionTitle>目标队列 · L3（启发式 Ĝ 近似排序）</SectionTitle>
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        <Badge tone="ok">活跃 {byStatus.active ?? 0}</Badge>
        <Badge tone="warn">挂起 {byStatus.suspended ?? 0}</Badge>
        <Badge tone="neutral">完成 {byStatus.done ?? 0}</Badge>
        <Badge tone="danger">撤销 {byStatus.revoked ?? 0}</Badge>
        <span style={{ flex: 1 }} />
        <Badge tone="neutral">priority = 0.6·info_gain + 0.4·charter 权重</Badge>
      </div>

      <GlassCard style={{ padding: 8 }}>
        {loading && <Empty>加载中…</Empty>}
        {!loading && items.length === 0 && <Empty>队列为空——先跑深周期合成目标</Empty>}
        {items.map((g) => (
          <div className="row row-enter" key={g.goal_id}>
            <div className="row-main">
              <div className="row-title">{g.title}</div>
              <div className="row-sub">
                {g.description.slice(0, 110)}
                {g.description.length > 110 ? "…" : ""}
              </div>
              <div className="row-sub" style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
                <Badge tone="accent">{TEMPLATE_LABEL[g.template_id] ?? g.template_id}</Badge>
                <Badge tone="neutral">template-based</Badge>
                <Badge tone={g.risk_level === "R3" ? "danger" : g.risk_level === "R2" ? "warn" : "ok"}>
                  {g.risk_level} 只读
                </Badge>
                <Badge tone="neutral">成功判据：{g.success_criteria}</Badge>
              </div>
            </div>
            <div className="row-side" style={{ flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div className="prio">
                  <span style={{ transform: `scaleX(${Math.min(g.priority, 1)})` }} />
                </div>
                <span className="num" style={{ fontSize: 13, fontWeight: 700, width: 40, textAlign: "right" }}>
                  {g.priority.toFixed(2)}
                </span>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button className="btn small" onClick={() => void act(g.goal_id, "suspended")}>
                  挂起
                </button>
                <button className="btn small ok" onClick={() => void act(g.goal_id, "done")}>
                  完成
                </button>
                <button className="btn small danger" onClick={() => void act(g.goal_id, "revoked")}>
                  撤销
                </button>
              </div>
            </div>
          </div>
        ))}
      </GlassCard>
    </>
  );
}
