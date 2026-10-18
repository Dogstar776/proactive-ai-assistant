import { useEffect, useMemo, useState } from "react";
import { api, type ObservedEvent } from "../api/client";
import { Badge, Empty, GlassCard, SectionTitle, SourceBadge, fmtDateTime } from "../components";

const KINDS = [
  { id: "", label: "全部" },
  { id: "calendar_event", label: "日程" },
  { id: "todo", label: "待办" },
  { id: "note", label: "笔记" },
  { id: "feed_item", label: "信息流" },
  { id: "reminder", label: "提醒" },
];

export default function EventsView({ live }: { live: ObservedEvent[] }) {
  const [items, setItems] = useState<ObservedEvent[]>([]);
  const [kind, setKind] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .events(kind ? { kind } : undefined)
      .then((d) => setItems(d.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [kind]);

  const merged = useMemo(() => {
    const seen = new Set(items.map((i) => i.event_id));
    return [...live.filter((e) => !kind || e.kind === kind).filter((e) => !seen.has(e.event_id)), ...items];
  }, [items, live, kind]);

  return (
    <>
      <SectionTitle>观测事件流 · L1</SectionTitle>
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        {KINDS.map((k) => (
          <button
            key={k.id || "all"}
            className={`btn small${kind === k.id ? " primary" : ""}`}
            onClick={() => setKind(k.id)}
          >
            {k.label}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        <Badge tone="neutral">provenance 溯源 · chain_depth</Badge>
      </div>

      <GlassCard style={{ padding: 8 }}>
        {loading && items.length === 0 && <Empty>加载中…</Empty>}
        {!loading && merged.length === 0 && <Empty>暂无事件——先到「认知环」跑一次轻观测周期</Empty>}
        {merged.map((ev) => (
          <div className="row row-enter" key={ev.event_id}>
            <div className="row-main">
              <div className="row-title">{ev.title}</div>
              <div className="row-sub">
                {ev.summary || (ev.content ?? "").slice(0, 80) || "（无摘要）"}
              </div>
            </div>
            <div className="row-side">
              <SourceBadge source={ev.source} />
              <Badge tone="neutral">depth {ev.chain_depth}</Badge>
              {ev.event_time && <Badge tone="warn">{fmtDateTime(ev.event_time)}</Badge>}
              {ev.importance >= 0.5 && <Badge tone="danger">重要度 {ev.importance.toFixed(2)}</Badge>}
              <span className="num" style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                {fmtDateTime(ev.observed_at)}
              </span>
            </div>
          </div>
        ))}
      </GlassCard>
    </>
  );
}
