import { useEffect, useRef, useState } from "react";
import type { ObservedEvent } from "../api/client";

/* FL-PCL 五层认知环：观测 → 自省 → 目标 → 门控 → 记忆回写 →（回到观测） */

const NODES = [
  { key: "observe", label: "观测", sub: "L1", sources: ["ics", "markdown_notes", "rss"] },
  { key: "introspect", label: "自省", sub: "L2", sources: ["introspection"] },
  { key: "goal", label: "目标", sub: "L3", sources: [] },
  { key: "gate", label: "门控", sub: "L5", sources: ["gateway"] },
  { key: "memory", label: "回写", sub: "L4", sources: [] },
] as const;

const R = 118;
const CX = 160;
const CY = 160;

function polar(i: number, total: number, r: number) {
  const angle = (i / total) * Math.PI * 2 - Math.PI / 2;
  return { x: CX + r * Math.cos(angle), y: CY + r * Math.sin(angle) };
}

export default function LoopRing({
  live,
  center,
}: {
  live: ObservedEvent[];
  center: React.ReactNode;
}) {
  const [active, setActive] = useState<Record<string, number>>({});
  const lastSeen = useRef<string>("");

  /* 实时事件 → 对应节点脉冲（同一条事件只触发一次） */
  useEffect(() => {
    if (!live.length) return;
    const ev = live[0];
    if (ev.event_id === lastSeen.current) return;
    lastSeen.current = ev.event_id;
    const node = NODES.find((n) => (n.sources as readonly string[]).includes(ev.source));
    if (!node) return;
    setActive((prev) => ({ ...prev, [node.key]: (prev[node.key] ?? 0) + 1 }));
    const timer = window.setTimeout(
      () => setActive((prev) => ({ ...prev, [node.key]: Math.max(0, (prev[node.key] ?? 1) - 1) })),
      1400
    );
    return () => window.clearTimeout(timer);
  }, [live]);

  return (
    <svg viewBox="0 0 320 320" style={{ width: "100%", maxWidth: 420 }}>
      <defs>
        <linearGradient id="ringStroke" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0a84ff" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#5e5ce6" stopOpacity="0.9" />
        </linearGradient>
        <filter id="soft" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
      </defs>

      {/* 闭环轨道 */}
      <circle
        cx={CX}
        cy={CY}
        r={R}
        fill="none"
        stroke="url(#ringStroke)"
        strokeWidth="1.5"
        strokeDasharray="2 7"
        strokeLinecap="round"
        opacity="0.65"
      >
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 160 160"
          to="360 160 160"
          dur="42s"
          repeatCount="indefinite"
        />
      </circle>

      {/* 流动光点（闭环优先于流水线：论文 3.0） */}
      <circle r="4" fill="#0a84ff" filter="url(#soft)">
        <animateMotion dur="7s" repeatCount="indefinite" path={`M ${CX} ${CY - R} a ${R} ${R} 0 1 1 -0.01 0`} />
      </circle>
      <circle r="2.5" fill="#5e5ce6" filter="url(#soft)" opacity="0.8">
        <animateMotion
          dur="7s"
          begin="2.3s"
          repeatCount="indefinite"
          path={`M ${CX} ${CY - R} a ${R} ${R} 0 1 1 -0.01 0`}
        />
      </circle>

      {/* 五层节点 */}
      {NODES.map((n, i) => {
        const p = polar(i, NODES.length, R);
        const on = (active[n.key] ?? 0) > 0;
        return (
          <g key={n.key} className={`loop-node${on ? " active" : ""}`}>
            <circle
              cx={p.x}
              cy={p.y}
              r={on ? 34 : 31}
              fill={on ? "rgba(10,132,255,0.16)" : "rgba(255,255,255,0.72)"}
              stroke={on ? "#0a84ff" : "rgba(120,130,160,0.28)"}
              strokeWidth={on ? 2 : 1}
              style={{ transition: "all 320ms cubic-bezier(0.32,0.72,0,1)" }}
            />
            <text
              x={p.x}
              y={p.y - 1}
              textAnchor="middle"
              fontSize="14"
              fontWeight="700"
              fill="#1d1d1f"
              style={{ fontFamily: "var(--font-cn)" }}
            >
              {n.label}
            </text>
            <text
              x={p.x}
              y={p.y + 14}
              textAnchor="middle"
              fontSize="9.5"
              fontWeight="600"
              fill="rgba(60,60,67,0.5)"
              style={{ fontFamily: "var(--font-num)" }}
            >
              {n.sub}
            </text>
          </g>
        );
      })}

      {/* 中心指标 */}
      <circle cx={CX} cy={CY} r={R - 44} fill="rgba(255,255,255,0.55)" stroke="rgba(255,255,255,0.9)" />
      {center}
    </svg>
  );
}
