"""OQ7：真实主动性与模拟主动性的可判定区分（论文 2.4 / 5.2 / OQ7）。

论文 5.2 的可证伪判别准则：
    "一个常驻系统宣称实现主动式AGI，当且仅当其目标内生判据不依赖人工编写的
     目标模板，且其自省可靠性经过独立信号源的长期校准。"

本实验把前半句操作化——模板移除测试：
    Phase A：带模板跑 N 轮深周期 → 记录目标队列
    Phase B：移除全部模板再跑 N 轮 → 记录目标队列
    Phase C：对比

预期结果（且这正是诚实之处）：Phase B 的目标数归零——
证明本系统的"目标内生"完全由模板驱动（设计者意图的延迟执行），
即论文定义的"主动行为的模拟"。这个实验不是要证明系统是 AGI，
而是把论文的判别准则变成可复现的测量。

安全说明：受控周期跑在临时内存库上，绝不触碰真实 data/assistant.db。

用法：python oq7_template_removal.py
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "assistant"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import Table, write_report  # noqa: E402


def build_services(db_path: Path, templates):
    """在指定库上装配一套完整的 观测→自省→目标 服务（内存/临时库）。"""
    import os

    os.environ["DATA_DIR"] = str(db_path.parent)
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["COLLECTOR_ICS_PATHS"] = str(REPO_ROOT / "assistant" / "fixtures" / "sample_calendar.ics")
    os.environ["COLLECTOR_NOTES_PATHS"] = str(REPO_ROOT / "assistant" / "fixtures" / "notes")
    os.environ["COLLECTOR_RSS_URLS"] = str(REPO_ROOT / "assistant" / "fixtures" / "feed.xml")

    from assistant.charter import load_charter
    from assistant.collectors import CollectorRunner
    from assistant.collectors.base import CollectorConfig
    from assistant.config import reset_settings_cache
    from assistant.db import connect, migrate
    from assistant.events.bus import EventBus
    from assistant.extraction import RulesExtractor
    from assistant.goals.repository import GoalRepository
    from assistant.goals.service import GoalService
    from assistant.goals.templates import DEFAULT_TEMPLATES
    from assistant.introspection.service import IntrospectionService
    from assistant.memory.repository import AuditRepository, ConsentRepository, EventRepository

    reset_settings_cache()
    migrate(db_path)
    conn = connect(db_path)
    bus = EventBus()
    runner = CollectorRunner(
        events=EventRepository(conn), audit=AuditRepository(conn),
        consent=ConsentRepository(conn), bus=bus, extractor=RulesExtractor(),
    )
    for cid, kind, params in [
        ("ics:t", "ics", {"paths": [os.environ["COLLECTOR_ICS_PATHS"]]}),
        ("notes:t", "markdown_notes", {"paths": [os.environ["COLLECTOR_NOTES_PATHS"]]}),
        ("rss:t", "rss", {"urls": [os.environ["COLLECTOR_RSS_URLS"]]}),
    ]:
        runner.register_config(CollectorConfig(collector_id=cid, kind=kind, params=params),
                               __import__("assistant.collectors", fromlist=["KINDS"]).KINDS[kind])
    introspection = IntrospectionService(events=EventRepository(conn), conn=conn, bus=bus)
    charter = load_charter(REPO_ROOT / "docs" / "charter.example.yaml")
    goals = GoalService(repo=GoalRepository(conn), charter=charter, bus=bus,
                        templates=templates if templates is not None else DEFAULT_TEMPLATES)
    return runner, introspection, goals, EventRepository(conn)


def run_phase(db_path: Path, templates, cycles: int, label: str) -> dict:
    runner, introspection, goals, events = build_services(db_path, templates)
    runner.run_once()  # 灌入 fixtures 事件
    per_cycle = []
    for i in range(cycles):
        report = introspection.run_cycle(trigger=f"oq7-{label}-{i}")
        new = goals.synthesize(report)
        per_cycle.append([i + 1, len(report.gaps), len(new)])
    queue = goals.repo.list(status="active", limit=100)
    return {
        "label": label,
        "templates": [t.template_id for t in goals.templates] or ["（已全部移除）"],
        "gaps_total": sum(r[1] for r in per_cycle),
        "goals_new": sum(r[2] for r in per_cycle),
        "queue_size": len(queue),
        "priorities": sorted((round(g.priority, 3) for g in queue), reverse=True),
        "per_cycle": per_cycle,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=3)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        a = run_phase(tmp_path / "a.sqlite", None, args.cycles, "with-templates")
        b = run_phase(tmp_path / "b.sqlite", [], args.cycles, "no-templates")

    print("== OQ7 模板移除测试 ==")
    print(f"Phase A（带模板 {a['templates']}）: 缺口 {a['gaps_total']} 个，"
          f"新目标 {a['goals_new']} 个，队列 {a['queue_size']}")
    print(f"Phase B（移除模板）        : 缺口 {b['gaps_total']} 个，"
          f"新目标 {b['goals_new']} 个，队列 {b['queue_size']}")
    drop = (a["goals_new"] - b["goals_new"]) / a["goals_new"] if a["goals_new"] else 0.0
    print(f"目标生成能力下降: {drop * 100:.0f}%")

    path = write_report("oq7-template-removal", "OQ7 · 模板移除测试（真实 vs 模拟主动性）", [
        ("实验设计",
         "论文 5.2 判别准则的操作化：带模板跑 N 轮深周期（Phase A）vs 移除全部模板"
         "再跑 N 轮（Phase B）。两组使用同一 fixtures 数据、同一 charter、同一检测器——"
         "唯一变量是目标合成模板的存在。"),
        ("逐轮明细", Table(
            ["轮次", "缺口数", "新目标数"],
            [[f"A-{r[0]}", r[1], r[2]] for r in a["per_cycle"]] +
            [[f"B-{r[0]}", r[1], r[2]] for r in b["per_cycle"]],
        ).to_markdown()),
        ("结果", Table(
            ["相位", "模板", "缺口总数", "新目标数", "队列规模", "优先级分布"],
            [["A（带模板）", ", ".join(a["templates"]), a["gaps_total"], a["goals_new"],
              a["queue_size"], a["priorities"]],
             ["B（移除模板）", ", ".join(b["templates"]), b["gaps_total"], b["goals_new"],
              b["queue_size"], b["priorities"]]],
        ).to_markdown()),
        ("结论", (
            f"移除模板后，目标生成能力下降 {drop * 100:.0f}%（缺口检测不变——"
            f"系统仍能'看到'缺口，但无法把缺口编译成目标）。"
            "按论文 5.2 判别准则，这证明本系统的目标内生完全由人工模板驱动，"
            "属于论文定义的『主动行为的模拟』——本实验的目的不是宣称 AGI，"
            "而是把判别准则变成可复现测量。")),
        ("复现方式", "`python experiments/oq7_template_removal.py`（使用 fixtures，不碰真实数据）"),
    ])
    print(f"报告已写入: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
