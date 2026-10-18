"""P6 实验公共库：数据库读取 + 报告写出。

所有实验脚本只读生产库（data/assistant.db），不写业务数据；
OQ7 的受控周期写在内存库上，不污染真实数据。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "assistant" / "data" / "assistant.db"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def connect_ro(db: Path) -> sqlite3.Connection:
    """只读方式打开生产库（WAL 下可安全并发读）。"""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params)]


def scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()):
    return conn.execute(sql, params).fetchone()[0]


@dataclass
class Table:
    headers: list[str]
    rows: list[list]

    def to_markdown(self) -> str:
        lines = ["| " + " | ".join(self.headers) + " |",
                 "|" + "|".join(["---"] * len(self.headers)) + "|"]
        for r in self.rows:
            lines.append("| " + " | ".join(str(c) for c in r) + " |")
        return "\n".join(lines)


def write_report(name: str, title: str, sections: list[tuple[str, str]]) -> Path:
    """把实验报告写到 experiments/reports/（本地证据，gitignored）。"""
    REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = REPORTS_DIR / f"{name}-{ts}.md"
    body = [f"# {title}", "",
            f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
            f"- 数据源：{DEFAULT_DB}", ""]
    for heading, content in sections:
        body += [f"## {heading}", "", content, ""]
    path.write_text("\n".join(body), encoding="utf-8")
    return path


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def day_of(iso: str) -> str:
    return iso[:10]
