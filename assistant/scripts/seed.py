"""种子数据生成 + 回放脚本。

用法（在 assistant/ 目录下）：
    python -m scripts.seed --reset     # 清库 + 灌种子 fixtures + 跑一轮采集
    python -m scripts.seed             # 仅跑一轮采集（幂等，可反复回放）

验证点：重复执行第二次时 items_inserted 应全为 0（幂等），
events 总数不变——这就是"种子数据回放"的验收标准。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"


def _settings(data_dir: Path):
    os_environ = {
        "DATA_DIR": str(data_dir),
        "LLM_PROVIDER": "mock",
        "COLLECTOR_ICS_PATHS": str(FIXTURES / "sample_calendar.ics"),
        "COLLECTOR_NOTES_PATHS": str(FIXTURES / "notes"),
        "COLLECTOR_RSS_URLS": str(FIXTURES / "feed.xml"),
        "LOG_LEVEL": "INFO",
    }
    import os

    for k, v in os_environ.items():
        os.environ[k] = v
    from assistant.config import Settings

    return Settings()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="删除 data/ 后重建")
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if args.reset and data_dir.exists():
        shutil.rmtree(data_dir)
        print(f"[seed] 已清空 {data_dir}")

    settings = _settings(data_dir)

    from assistant.collectors import KINDS, CollectorRunner
    from assistant.collectors.base import CollectorConfig
    from assistant.db import connect, migrate
    from assistant.events.bus import get_bus
    from assistant.extraction import RulesExtractor
    from assistant.logging_setup import setup_logging
    from assistant.memory.repository import AuditRepository, ConsentRepository, EventRepository

    setup_logging(settings.log_level)
    migrate(settings.db_path)
    conn = connect(settings.db_path)

    runner = CollectorRunner(
        events=EventRepository(conn),
        audit=AuditRepository(conn),
        consent=ConsentRepository(conn),
        bus=get_bus(),
        extractor=RulesExtractor(),
        granted_by="seed",
    )
    runner.register_config(
        CollectorConfig(collector_id="ics:seed", kind="ics",
                        params={"paths": settings.ics_paths and
                                [str(p) for p in settings.ics_paths]}),
        KINDS["ics"],
    )
    runner.register_config(
        CollectorConfig(collector_id="notes:seed", kind="markdown_notes",
                        params={"paths": [str(p) for p in settings.notes_paths]}),
        KINDS["markdown_notes"],
    )
    runner.register_config(
        CollectorConfig(collector_id="rss:seed", kind="rss",
                        params={"urls": settings.rss_urls}),
        KINDS["rss"],
    )

    results = runner.run_once()
    total = EventRepository(conn).count()
    print("\n[seed] 采集结果：")
    for r in results:
        print(f"  - {r.collector_id}: status={r.status} seen={r.items_seen} "
              f"inserted={r.items_inserted} dead_letter={len(r.dead_letter)}")
        for dl in r.dead_letter:
            print(f"      dead_letter: {dl}")
    print(f"[seed] 事件库总数: {total}")
    print("[seed] 再跑一次验证幂等：python -m scripts.seed（第二次 inserted 应全为 0）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
