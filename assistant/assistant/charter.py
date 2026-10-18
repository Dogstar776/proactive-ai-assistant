"""charter 加载与校验：论文 C_human（人类价值观外源锚定）的工程化。

优先级：data/charter.yaml（用户真实偏好，gitignored）→ docs/charter.example.yaml（示例）。
 charter 是 Git 版本管理的文本文件——"锚点可见、可审计、可回滚"本身即是设计主张。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from assistant.errors import ConfigurationError

_DEFAULT_CHARTER = (
    Path(__file__).resolve().parent.parent.parent
    / "docs"
    / "charter.example.yaml"
)


@dataclass
class Domain:
    name: str
    weight: float
    active: bool = True
    notes: str = ""


@dataclass
class Charter:
    version: int = 1
    owner: str = ""
    domains: list[Domain] = field(default_factory=list)
    value_anchors: list[dict] = field(default_factory=list)
    risk_policy: dict = field(default_factory=dict)
    quiet_hours: list[dict] = field(default_factory=list)
    intervention_budget: dict = field(default_factory=dict)
    preferences: list[str] = field(default_factory=list)
    source_path: str = ""

    def domain_weight(self, text: str) -> tuple[float, str | None]:
        """文本 → 最匹配的域权重（实用价值项的近似输入）。

        匹配规则：域名或其 notes 中的关键词出现在文本中。
        无匹配返回 (0.0, None)——不假装所有文本都能归域。
        """
        best = (0.0, None)
        for d in self.domains:
            if not d.active:
                continue
            keys = [d.name, *re.findall(r"[\u4e00-\u9fff]{2,}", d.notes or "")]
            if any(k and k in text for k in keys) and d.weight > best[0]:
                best = (d.weight, d.name)
        return best

    @property
    def max_proactive_per_day(self) -> int:
        return int(self.intervention_budget.get("max_proactive_per_day", 3))


def load_charter(path: Path | None = None) -> Charter:
    """加载 charter；文件缺失时回退示例并告警，绝不静默使用空锚定。"""
    candidates = ([path] if path else [Path("data/charter.yaml")]) + [_DEFAULT_CHARTER]
    for p in candidates:
        if p and p.exists():
            try:
                raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                raise ConfigurationError(f"charter 解析失败: {p} ({e})") from e
            if not isinstance(raw, dict):
                raise ConfigurationError(f"charter 顶层必须是映射: {p}")
            charter = Charter(
                version=int(raw.get("version", 1)),
                owner=str(raw.get("owner", "")),
                domains=[
                    Domain(
                        name=str(d.get("name", "")),
                        weight=float(d.get("weight", 0)),
                        active=bool(d.get("active", True)),
                        notes=str(d.get("notes", "")),
                    )
                    for d in raw.get("domains", [])
                    if isinstance(d, dict) and d.get("name")
                ],
                value_anchors=list(raw.get("value_anchors", [])),
                risk_policy=dict(raw.get("risk_policy", {})),
                quiet_hours=list(raw.get("quiet_hours", [])),
                intervention_budget=dict(raw.get("intervention_budget", {})),
                preferences=list(raw.get("preferences", [])),
                source_path=str(p),
            )
            if not charter.domains:
                raise ConfigurationError(f"charter 至少需要一个 domain: {p}")
            return charter
    raise ConfigurationError("未找到 charter 文件（data/charter.yaml 或示例文件）")
