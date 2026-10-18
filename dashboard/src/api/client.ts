/* 类型化 API 客户端 + SSE 订阅（ADR-0002：Base URL 走环境变量/代理） */

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body.message ?? message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export interface ObservedEvent {
  event_id: string;
  source: string;
  source_ref: string;
  kind: string;
  title: string;
  summary: string;
  content: string;
  event_time: string | null;
  observed_at: string;
  importance: number;
  tags: string[];
  extractor: string;
  provenance: string;
  chain_depth: number;
}

export interface Goal {
  goal_id: string;
  title: string;
  description: string;
  template_id: string;
  status: string;
  priority: number;
  info_gain: number;
  practical_value: number;
  risk_level: string;
  success_criteria: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface Reminder {
  reminder_id: string;
  goal_id: string | null;
  kind: string;
  title: string;
  body: string;
  risk_level: string;
  state: string;
  status: string;
  decision_reason: string;
  created_at: string;
}

export interface Gap {
  kind: string;
  title: string;
  detail: string;
  score: number;
  evidence: string[];
}

export interface IntrospectionReport {
  report_id: string;
  ts: string;
  trigger: string;
  summary: string;
  audit_metrics: Record<string, number>;
  gaps: Gap[];
}

export const api = {
  health: () => req<{ status: string }>("/health"),
  stats: () =>
    req<{ total: number; by_source: Record<string, number> }>("/api/v1/events/stats"),
  events: (params?: { kind?: string; source?: string; limit?: number }) => {
    const q = new URLSearchParams({ limit: String(params?.limit ?? 100) });
    if (params?.kind) q.set("kind", params.kind);
    if (params?.source) q.set("source", params.source);
    return req<{ items: ObservedEvent[]; stats: { total: number } }>(`/api/v1/events?${q}`);
  },
  runCollectors: () =>
    req<{ results: { collector_id: string; status: string; items_inserted: number }[] }>(
      "/api/v1/collectors/run",
      { method: "POST" }
    ),
  runDeepCycle: () =>
    req<{
      report_id: string;
      summary: string;
      gaps: Gap[];
      audit: Record<string, number>;
      new_goals: Goal[];
    }>("/api/v1/introspection/run?trigger=dashboard", { method: "POST" }),
  reports: () => req<{ items: IntrospectionReport[] }>("/api/v1/introspection/reports"),
  goals: (status?: string) =>
    req<{ items: Goal[]; stats: { by_status: Record<string, number> } }>(
      `/api/v1/goals${status ? `?status=${status}` : ""}`
    ),
  setGoalStatus: (id: string, status: string) =>
    req(`/api/v1/goals/${id}/status?status=${status}`, { method: "POST" }),
  runReminders: () =>
    req<{
      results: { evaluated: number; act: number; assist: number; ask: number; silence: number };
    }>("/api/v1/reminders/run", { method: "POST" }),
  reminders: (status?: string) =>
    req<{ items: Reminder[] }>(`/api/v1/reminders?limit=100${status ? `&status=${status}` : ""}`),
  approve: (id: string) =>
    req(`/api/v1/reminders/${id}/approve`, { method: "POST" }),
  reject: (id: string) => req(`/api/v1/reminders/${id}/reject`, { method: "POST" }),
  batch: (ids: string[], action: "approve" | "reject") =>
    req(`/api/v1/reminders/batch?action=${action}`, {
      method: "POST",
      body: JSON.stringify(ids),
    }),
  fatigue: () =>
    req<{
      counts: Record<string, number>;
      ask_total: number;
      approval_rate: number | null;
    }>("/api/v1/gateway/stats"),
  charter: () =>
    req<{
      parsed: {
        owner: string;
        domains: { name: string; weight: number; active: boolean; notes: string }[];
        quiet_hours: unknown[];
        intervention_budget: Record<string, number>;
        source_path: string;
      };
      yaml: string;
    }>("/api/v1/charter"),
  saveCharter: (yaml: string) =>
    req<{ status: string; path: string }>("/api/v1/charter", {
      method: "POST",
      body: JSON.stringify({ yaml }),
    }),
  systemStatus: () =>
    req<{
      provider: string;
      model: string;
      deep_cycles_per_day: number;
      daily_token_budget: number;
      data_dir: string;
    }>("/api/v1/system/status"),
  consents: () => req<{ items: { scope: string; revoked_at: string | null }[] }>("/api/v1/consents"),
  audit: (action?: string) =>
    req<{ items: { ts: string; action: string; status: string; target: string }[] }>(
      `/api/v1/audit?limit=50${action ? `&action=${action}` : ""}`
    ),
};

/* ── SSE：认知环实时事件流 ── */
export interface StreamFrame {
  event: string;
  data: ObservedEvent | { total: number; by_source: Record<string, number> };
}

export function subscribeStream(onFrame: (f: StreamFrame) => void): () => void {
  const es = new EventSource(`${BASE}/api/v1/stream`);
  const onObserved = (e: MessageEvent) =>
    onFrame({ event: "observed", data: JSON.parse(e.data) });
  const onStats = (e: MessageEvent) =>
    onFrame({ event: "stats", data: JSON.parse(e.data) });
  es.addEventListener("observed", onObserved as EventListener);
  es.addEventListener("stats", onStats as EventListener);
  return () => {
    es.removeEventListener("observed", onObserved as EventListener);
    es.removeEventListener("stats", onStats as EventListener);
    es.close();
  };
}
