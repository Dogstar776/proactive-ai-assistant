import type { ReactNode } from "react";

export function GlassCard({
  children,
  className = "",
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div className={`glass ${className}`} style={style}>
      {children}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "ok" | "warn" | "danger" | "neutral" | "accent";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Stat({
  label,
  value,
  unit,
  tone,
}: {
  label: string;
  value: string | number;
  unit?: string;
  tone?: "ok" | "warn" | "danger" | "neutral" | "accent";
}) {
  return (
    <GlassCard className="stat">
      <div className="k">{label}</div>
      <div className="v" style={tone ? { color: `var(--${tone})` } : undefined}>
        {value}
        {unit ? <small>{unit}</small> : null}
      </div>
    </GlassCard>
  );
}

const SOURCE_TONE: Record<string, "ok" | "warn" | "danger" | "neutral" | "accent"> = {
  ics: "accent",
  markdown_notes: "ok",
  rss: "warn",
  introspection: "neutral",
  gateway: "danger",
};

const SOURCE_LABEL: Record<string, string> = {
  ics: "日历",
  markdown_notes: "笔记",
  rss: "信息流",
  introspection: "自省",
  gateway: "门控",
};

export function SourceBadge({ source }: { source: string }) {
  return <Badge tone={SOURCE_TONE[source] ?? "neutral"}>{SOURCE_LABEL[source] ?? source}</Badge>;
}

export function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function fmtDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${fmtTime(iso)}`;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="section-title">{children}</div>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
