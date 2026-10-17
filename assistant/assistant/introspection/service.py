"""自省服务：一次"深周期"的编排（论文 3.2）。

缺口检测 → 一致性审计 → 自省报告入库 → 事件总线广播。
全部输出携带 `[B-simulated]` 语义：这是"主动行为的模拟"中自省侧的
工程近似，不是论文意义上可靠的元认知（ADR-0003 / ADR-0006）。
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from assistant.events.bus import EventBus
from assistant.introspection.detectors import (
    ContradictionDetector,
    DeadlinePrepDetector,
    Gap,
    GapDetector,
    ThemeClusterDetector,
)
from assistant.logging_setup import get_logger
from assistant.memory.repository import EventRepository
from assistant.models import ObservedEvent

logger = get_logger("introspection")


@dataclass
class AuditMetrics:
    """OQ4 记忆健康指标的工程近似子集。"""

    total_events: int = 0
    system_derived_ratio: float = 0.0   # 自生内容占比（论文 4.3 腐化载体）
    duplicate_ratio: float = 0.0        # 跨源重复率
    overdue_open: int = 0               # 过期未消项
    max_chain_depth: int = 0            # 生成链深度（0=原始经验）

    def to_dict(self) -> dict:
        return {
            "total_events": self.total_events,
            "system_derived_ratio": round(self.system_derived_ratio, 3),
            "duplicate_ratio": round(self.duplicate_ratio, 3),
            "overdue_open": self.overdue_open,
            "max_chain_depth": self.max_chain_depth,
        }


@dataclass
class IntrospectionReport:
    report_id: str
    ts: str
    trigger: str
    gaps: list[Gap] = field(default_factory=list)
    audit: AuditMetrics = field(default_factory=AuditMetrics)
    summary: str = ""

    def to_row(self) -> dict:
        return {
            "report_id": self.report_id,
            "ts": self.ts,
            "trigger": self.trigger,
            "gaps": json.dumps([vars(g) for g in self.gaps], ensure_ascii=False),
            "contradictions": json.dumps(
                [vars(g) for g in self.gaps if g.kind == "contradiction"], ensure_ascii=False
            ),
            "audit_metrics": json.dumps(self.audit.to_dict(), ensure_ascii=False),
            "summary": self.summary,
            "extractor": "rules",
            "simulated": 1,
        }


class IntrospectionService:
    def __init__(
        self,
        events: EventRepository,
        conn,  # ThreadLocalConnection 或 sqlite3.Connection
        bus: EventBus,
        detectors: list[GapDetector] | None = None,
    ) -> None:
        self.events = events
        self.conn = conn
        self.bus = bus
        self.detectors = detectors or [
            DeadlinePrepDetector(),
            ThemeClusterDetector(),
            ContradictionDetector(),
        ]

    def run_cycle(self, trigger: str = "manual", *, limit: int = 500) -> IntrospectionReport:
        now = datetime.now(UTC)
        recent: list[ObservedEvent] = self.events.list(limit=limit)

        gaps: list[Gap] = []
        for det in self.detectors:
            try:
                gaps.extend(det.detect(recent, now=now))
            except Exception:  # 单检测器失败不中断整轮
                logger.exception("detector %s failed", det.kind)

        audit = self._audit(recent, now)
        report = IntrospectionReport(
            report_id=str(uuid.uuid4()),
            ts=now.isoformat(),
            trigger=trigger,
            gaps=gaps,
            audit=audit,
            summary=self._summarize(gaps, audit),
        )
        self._store(report)
        self.bus.publish(self._to_event(report))
        log = logger.info if gaps else logger.info
        log("introspection.cycle trigger=%s gaps=%d audit=%s",
            trigger, len(gaps), audit.to_dict())
        return report

    def list_reports(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM introspection_reports ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            for k in ("gaps", "contradictions", "audit_metrics"):
                d[k] = json.loads(d.get(k) or "[]" if k != "audit_metrics" else d.get(k) or "{}")
            out.append(d)
        return out

    def _store(self, report: IntrospectionReport) -> None:
        self.conn.execute(
            """
            INSERT INTO introspection_reports
                (report_id, ts, trigger, gaps, contradictions, audit_metrics,
                 summary, extractor, simulated)
            VALUES
                (:report_id, :ts, :trigger, :gaps, :contradictions, :audit_metrics,
                 :summary, :extractor, :simulated)
            """,
            report.to_row(),
        )
        self.conn.commit()

    @staticmethod
    def _audit(events: list[ObservedEvent], now: datetime) -> AuditMetrics:
        from assistant.introspection.detectors import _parse_time

        total = len(events)
        if total == 0:
            return AuditMetrics()
        system = sum(1 for e in events if e.provenance == "system_derived")
        titles: dict[str, set[str]] = {}
        for e in events:
            key = "".join(e.title.split())
            titles.setdefault(key, set()).add(e.source)
        dup = sum(1 for v in titles.values() if len(v) > 1)
        overdue = sum(
            1 for e in events
            if e.kind == "todo" and (w := _parse_time(e)) and w < now
        )
        return AuditMetrics(
            total_events=total,
            system_derived_ratio=system / total,
            duplicate_ratio=dup / len(titles) if titles else 0.0,
            overdue_open=overdue,
            max_chain_depth=max((e.chain_depth for e in events), default=0),
        )

    @staticmethod
    def _summarize(gaps: list[Gap], audit: AuditMetrics) -> str:
        if not gaps:
            return f"[B-simulated] 未检测到缺口；审计指标 {audit.to_dict()}"
        top = sorted(gaps, key=lambda g: -g.score)[0]
        return (
            f"[B-simulated] 检出 {len(gaps)} 个缺口，最高优先：「{top.title}」"
            f"（score={top.score}）；审计指标 {audit.to_dict()}"
        )


    @staticmethod
    def _to_event(report: IntrospectionReport) -> ObservedEvent:
        """自省报告转为系统内生事件上总线。

        语义：provenance=system_derived、chain_depth=1（对原始观测的一次派生）——
        这正是论文 4.3 / OQ4 要测量的"自生内容"，让它进入事件流而非旁路。
        """
        return ObservedEvent(
            source="introspection",
            source_ref="deep_cycle",
            consent_id="system:internal",  # 纯内部认知操作，R0 默认放行（论文 3.5）
            kind="introspection_report",
            title=f"自省报告：检出 {len(report.gaps)} 个缺口",
            summary=report.summary,
            content=json.dumps(
                {"gaps": [vars(g) for g in report.gaps], "audit": report.audit.to_dict()},
                ensure_ascii=False,
            ),
            observed_at=report.ts,
            importance=max((g.score for g in report.gaps), default=0.0),
            tags=["introspection", "B-simulated"],
            extractor="rules",
            provenance="system_derived",
            chain_depth=1,
            metadata={"report_id": report.report_id, "trigger": report.trigger},
        )
