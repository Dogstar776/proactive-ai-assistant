"""提醒周期 CLI：跑一次 目标 → 四态门控 → 触达/沉默。

用法（assistant/ 目录下）：
    python -m scripts.run_reminder_cycle
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.parse_args()

    from assistant.api.deps import get_reminder_service

    svc = get_reminder_service()
    result = svc.run_cycle()
    print("\n[reminders] 本轮门控结果:")
    print(f"  evaluated={result['evaluated']} act={result['act']} "
          f"assist={result['assist']} ask={result['ask']} "
          f"silence={result['silence']} expired={result['expired']}")
    print("[reminders] 最近 10 条干预:")
    for r in svc.repo.list(limit=10):
        print(f"  [{r.status:<10}] {r.risk_level} {r.title[:38]} | {r.decision_reason[:40]}")
    print(f"[reminders] 授权疲劳自检: {json.dumps(svc.fatigue_stats(), ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
