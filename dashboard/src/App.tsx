import { Component, useEffect, useMemo, useState } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { api, subscribeStream, type ObservedEvent } from "./api/client";
import { GlassCard } from "./components";
import LoopView from "./views/LoopView";
import EventsView from "./views/EventsView";
import IntrospectionView from "./views/IntrospectionView";
import GoalsView from "./views/GoalsView";
import RemindersView from "./views/RemindersView";
import CharterView from "./views/CharterView";
import CostsView from "./views/CostsView";

/* 错误边界：单个视图崩溃不得白屏整个应用 */
class ErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state = { error: null as string | null };

  static getDerivedStateFromError(e: Error) {
    return { error: e.message };
  }

  componentDidCatch(e: Error, info: ErrorInfo) {
    console.error("view crash:", e, info);
  }

  render() {
    if (this.state.error) {
      return (
        <GlassCard style={{ padding: 28 }}>
          <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>这个视图出错了</div>
          <div style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 14 }}>
            {this.state.error}
          </div>
          <button className="btn primary" onClick={() => this.setState({ error: null })}>
            重试
          </button>
        </GlassCard>
      );
    }
    return this.props.children;
  }
}

const TABS = [
  { id: "loop", label: "认知环" },
  { id: "events", label: "事件流" },
  { id: "introspection", label: "自省" },
  { id: "goals", label: "目标" },
  { id: "reminders", label: "提醒门控" },
  { id: "charter", label: "Charter" },
  { id: "costs", label: "成本" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("loop");
  const [online, setOnline] = useState(false);
  const [live, setLive] = useState<ObservedEvent[]>([]);

  /* SSE 实时事件流：认知环的"活水" */
  useEffect(() => {
    let timer: number | undefined;
    const check = async () => {
      try {
        await api.health();
        setOnline(true);
      } catch {
        setOnline(false);
      }
    };
    void check();
    timer = window.setInterval(check, 15000);
    const unsub = subscribeStream((frame) => {
      if (frame.event === "observed") setLive((prev) => [frame.data as ObservedEvent, ...prev].slice(0, 60));
    });
    return () => {
      window.clearInterval(timer);
      unsub();
    };
  }, []);

  const view = useMemo(() => {
    switch (tab) {
      case "loop":
        return <LoopView live={live} />;
      case "events":
        return <EventsView live={live} />;
      case "introspection":
        return <IntrospectionView />;
      case "goals":
        return <GoalsView />;
      case "reminders":
        return <RemindersView />;
      case "charter":
        return <CharterView />;
      case "costs":
        return <CostsView />;
    }
  }, [tab, live]);

  return (
    <>
      <div className="app-bg" />
      <div className="app">
        <header className="app-header">
          <div className="app-title">
            <span className={`dot${online ? "" : " offline"}`} />
            主动式 AI 助理
            <span className="num" style={{ fontSize: 13, color: "var(--text-3)", fontWeight: 600 }}>
              FL-PCL · 受限常驻实例
            </span>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <span className="badge neutral">[B-simulated]</span>
            <span className="badge accent">本地优先</span>
          </div>
        </header>
        <main className="app-main">
          <div className="view" key={tab}>
            <ErrorBoundary>{view}</ErrorBoundary>
          </div>
        </main>
      </div>
      <nav className="capsule-nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "active" : ""}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
    </>
  );
}
