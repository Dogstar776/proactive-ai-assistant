"""OQ4：常驻记忆库的认知健康度量（论文 4.3 / OQ4 的工程近似子集）。

测量（全部来自生产库的自动记录，无需用户任何操作）：
  - provenance 分布：user_injected / system_derived / external_retrieved
  - 生成链深度分布：chain_depth（0=原始经验，1=一次派生…）
  - 自生内容占比趋势：system_derived_ratio（论文 4.3 腐化载体）
  - 跨源重复率：duplicate_ratio
  - 事件增长曲线与过期未消项

用法：python memory_health.py
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import DEFAULT_DB, Table, connect_ro, day_of, pct, rows, write_report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = ap.parse_args()

    if not args.db.exists():
        print(f"数据库不存在: {args.db}")
        return 1
    conn = connect_ro(args.db)
    events = rows(conn, "SELECT * FROM observed_events ORDER BY observed_at")
    reports = rows(conn, "SELECT * FROM introspection_reports ORDER BY ts")

    if not events:
        print("无事件记录——先跑几次采集周期")
        return 1

    # provenance 分布
    prov: Counter = Counter(e["provenance"] for e in events)
    total = len(events)

    # 链深分布
    depth: Counter = Counter(e["chain_depth"] for e in events)

    # 来源分布
    src: Counter = Counter(e["source"] for e in events)

    # 自省报告的审计指标趋势
    trend_rows = []
    for r in reports:
        m = r.get("audit_metrics") or "{}"
        import json
        m = json.loads(m) if isinstance(m, str) else m
        trend_rows.append([
            day_of(r["ts"]),
            m.get("total_events", 0),
            pct(m.get("system_derived_ratio", 0)),
            pct(m.get("duplicate_ratio", 0)),
            m.get("overdue_open", 0),
            m.get("max_chain_depth", 0),
        ])

    # 增长曲线（按天）
    per_day: Counter = Counter(day_of(e["observed_at"]) for e in events)
    growth_rows = [[d, n] for d, n in sorted(per_day.items())]

    print("== OQ4 记忆健康 ==")
    print(f"事件总数 {total}；provenance: {dict(prov)}")
    print(f"链深分布: {dict(sorted(depth.items()))}")
    print(f"自生内容占比: {pct(prov.get('system_derived', 0) / total)}")

    path = write_report("memory-health", "OQ4 · 常驻记忆库认知健康", [
        ("provenance 分布", Table(
            ["来源类型", "数量", "占比"],
            [[k, v, pct(v / total)] for k, v in prov.most_common()],
        ).to_markdown()),
        ("生成链深度分布", Table(
            ["chain_depth", "数量", "含义"],
            [[d, n, "原始经验" if d == 0 else f"{d} 次派生"] for d, n in sorted(depth.items())],
        ).to_markdown()),
        ("连接器来源", Table(["source", "数量"], [[k, v] for k, v in src.most_common()]).to_markdown()),
        ("自省审计指标趋势", Table(
            ["日期", "事件总数", "自生内容占比", "跨源重复率", "过期未消", "最大链深"],
            trend_rows,
        ).to_markdown() if trend_rows else "尚无自省报告"),
        ("事件增长曲线", Table(["日期", "新增事件"], growth_rows).to_markdown()),
        ("健康判读（论文 4.3）",
         "- 自生内容占比持续上升 = 系统在自己的输出上运行（记忆腐化载体）；\n"
         "- 链深 >1 的条目占比上升 = 生成链拉长，语义保真度衰减；\n"
         "- 跨源重复率上升 = 检索噪声增大，需触发 contradiction-scan 目标；\n"
         "- 本指标随 14 天运行积累，是论文二 OQ4 一节的数据基础。"),
    ])
    print(f"报告已写入: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
