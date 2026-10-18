import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Badge, GlassCard, SectionTitle } from "../components";

export default function CharterView() {
  const [yaml, setYaml] = useState("");
  const [domains, setDomains] = useState<{ name: string; weight: number; active: boolean }[]>([]);
  const [sourcePath, setSourcePath] = useState("");
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .charter()
      .then((d) => {
        setYaml(d.yaml);
        setDomains(d.parsed.domains);
        setSourcePath(d.parsed.source_path);
      })
      .catch(() => setMsg({ tone: "danger", text: "加载失败：后端未连接" }));
  }, []);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      const r = await api.saveCharter(yaml);
      setMsg({ tone: "ok", text: `已保存并热重载：${r.path}` });
      const d = await api.charter();
      setDomains(d.parsed.domains);
    } catch (e) {
      setMsg({ tone: "danger", text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <SectionTitle>Charter · 人类偏好锚定（C_human 工程化）</SectionTitle>
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
        <Badge tone="accent">当前源：{sourcePath || "—"}</Badge>
        <Badge tone="neutral">保存后热重载，无需重启</Badge>
        <span style={{ flex: 1 }} />
        {msg && <Badge tone={msg.tone}>{msg.text}</Badge>}
        <button className="btn primary" disabled={saving} onClick={() => void save()}>
          {saving ? "保存中…" : "保存并重载"}
        </button>
      </div>

      <div className="loop-wrap" style={{ gridTemplateColumns: "1fr 300px" }}>
        <GlassCard style={{ padding: 12 }}>
          <textarea
            className="editor"
            value={yaml}
            onChange={(e) => setYaml(e.target.value)}
            spellCheck={false}
          />
        </GlassCard>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <GlassCard style={{ padding: 18 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-2)", marginBottom: 12 }}>
              域权重（目标排序的实用价值项）
            </div>
            {domains.map((d) => (
              <div key={d.name} style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 5 }}>
                  <span style={{ fontWeight: 600 }}>{d.name}</span>
                  <span className="num" style={{ color: "var(--text-2)" }}>
                    {d.weight}
                    {d.active ? "" : " · 停用"}
                  </span>
                </div>
                <div className="prio" style={{ width: "100%" }}>
                  <span style={{ transform: `scaleX(${Math.min(d.weight / 10, 1)})` }} />
                </div>
              </div>
            ))}
            {domains.length === 0 && <div style={{ color: "var(--text-3)", fontSize: 13 }}>暂无域</div>}
          </GlassCard>

          <GlassCard style={{ padding: 18 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-2)", marginBottom: 8 }}>
              为什么有这个东西
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.75 }}>
              论文 3.3 的关键改造：目标内生的"值得做"判据必须由人类价值观外源锚定，
              否则目标生成滑向纯信息增益驱动的无约束探索。charter 就是这个锚点——
              人类撰写、Git 版本管理、每次目标合成时读取。
            </div>
          </GlassCard>
        </div>
      </div>
    </>
  );
}
