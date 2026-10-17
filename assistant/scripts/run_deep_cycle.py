"""深周期 CLI：跑一次"自省 → 目标合成"（论文 3.2→3.3）。

用法（assistant/ 目录下）：
    python -m scripts.run_deep_cycle            # 跑一轮深周期
    python -m scripts.run_deep_cycle --trigger scheduled

对应 ADR-0005 低频深周期；P6 起由实验脚本按不同周期率调用。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trigger", default="cli")
    args = ap.parse_args()

    from assistant.api.deps import get_deep_cycle_service

    svc = get_deep_cycle_service()
    result = svc.run(trigger=args.trigger)

    print(f"\n[deep-cycle] 自省报告 {result['report_id']}")
    print(f"[deep-cycle] {result['summary']}")
    print(f"[deep-cycle] 缺口 {len(result['gaps'])} 个：")
    for g in result["gaps"]:
        print(f"  - [{g['kind']}] {g['title']} (score={g['score']})")
    print(f"[deep-cycle] 新入队目标 {len(result['new_goals'])} 个：")
    for g in result["new_goals"]:
        print(f"  - [{g['template_id']}] p={g['priority']} {g['title']}")
    if not result["new_goals"]:
        print("  （无新目标：缺口未匹配任何模板，或已入队过——幂等）")
    print(f"[deep-cycle] 审计指标: {json.dumps(result['audit'], ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
