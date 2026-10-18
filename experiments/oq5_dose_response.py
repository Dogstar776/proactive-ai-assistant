"""OQ5：认知周期剂量—效应曲线（论文 4.4 / OQ5）。

测量：不同干预频率下，用户的真实采纳率、打扰感与授权疲劳趋势。
数据全自动来自 reminders 表——用户唯一的动作是对通知点批准/拒绝（或不点）。

用法：
    python oq5_dose_response.py            # 全量分析
    python oq5_dose_response.py --days 7   # 只看最近 7 天
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import DEFAULT_DB, Table, connect_ro, day_of, pct, rows, write_report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0, help="只看最近 N 天（0=全部）")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = ap.parse_args()

    if not args.db.exists():
        print(f"数据库不存在: {args.db}（先跑几次深周期/提醒周期产生数据）")
        return 1
    conn = connect_ro(args.db)
    since = ""
    if args.days > 0:
        since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    sql = "SELECT * FROM reminders"
    params: tuple = ()
    if since:
        sql += " WHERE created_at >= ?"
        params = (since,)
    reminders = rows(conn, sql, params)

    if not reminders:
        print("无提醒记录——先通过 API/CLI 跑几个提醒周期")
        return 1

    # ── 按天聚合 ──
    per_day: dict[str, Counter] = defaultdict(Counter)
    for r in reminders:
        d = day_of(r["created_at"])
        per_day[d][r["state"]] += 1
        per_day[d][f"status:{r['status']}"] += 1

    day_rows = []
    for d in sorted(per_day):
        c = per_day[d]
        act = c.get("act", 0)
        silence = c.get("silence", 0)
        approved = c.get("status:approved", 0)
        rejected = c.get("status:rejected", 0)
        expired = c.get("status:expired", 0)
        decided = approved + rejected
        day_rows.append([
            d, act, silence, c.get("assist", 0), c.get("ask", 0),
            approved, rejected, expired,
            pct(approved / decided) if decided else "—",
        ])

    # ── 总体采纳率（OQ5 主指标） ──
    approved = sum(1 for r in reminders if r["status"] == "approved")
    rejected = sum(1 for r in reminders if r["status"] == "rejected")
    expired = sum(1 for r in reminders if r["status"] == "expired")
    delivered = sum(1 for r in reminders if r["status"] == "delivered")
    pending = sum(1 for r in reminders if r["status"] == "pending")
    decided = approved + rejected

    # ── 沉默原因分布（论文 3.5 的沉默经济学） ──
    silence_reasons: Counter = Counter()
    for r in reminders:
        if r["state"] == "silence":
            key = r["decision_reason"].split("(")[0].strip() or r["decision_reason"]
            silence_reasons[key] += 1

    # ── 授权疲劳趋势（按决定顺序的滑动批准率） ──
    decided_seq = [r for r in reminders if r["status"] in ("approved", "rejected")]
    decided_seq.sort(key=lambda r: r["created_at"])
    fatigue_rows = []
    window = 5
    for i in range(0, len(decided_seq), window):
        chunk = decided_seq[i:i + window]
        a = sum(1 for r in chunk if r["status"] == "approved")
        fatigue_rows.append([
            f"#{i + 1}-{i + len(chunk)}", len(chunk), a,
            pct(a / len(chunk)) if chunk else "—",
        ])

    print("== OQ5 剂量—效应 ==")
    print(f"提醒总数 {len(reminders)}：delivered {delivered} / pending {pending} / "
          f"approved {approved} / rejected {rejected} / expired {expired} / suppressed "
          f"{sum(1 for r in reminders if r['state'] == 'silence')}")
    if decided:
        print(f"采纳率（approved/(approved+rejected)）= {pct(approved / decided)}")
    if silence_reasons:
        print("沉默原因分布：", dict(silence_reasons))

    path = write_report("oq5-dose-response", "OQ5 · 认知周期剂量—效应", [
        ("按天聚合", Table(
            ["日期", "act", "silence", "assist", "ask", "批准", "拒绝", "超时", "当日采纳率"],
            day_rows,
        ).to_markdown()),
        ("总体指标",
         f"- 提醒总数：{len(reminders)}\n- 已触达未回应（delivered）：{delivered}\n"
         f"- 待确认（pending）：{pending}\n- 批准：{approved} · 拒绝：{rejected} · 超时默认拒绝：{expired}\n"
         f"- **采纳率：{pct(approved / decided) if decided else '数据不足'}**\n"
         f"- 超时未决定率：{pct((expired + pending) / len(reminders))}（授权疲劳信号）"),
        ("沉默原因分布", Table(["原因", "次数"], [[k, v] for k, v in silence_reasons.most_common()]).to_markdown()
         if silence_reasons else "无沉默记录"),
        ("授权疲劳趋势（每 5 次决定的滑动窗口）",
         Table(["决定区间", "决定数", "批准", "批准率"], fatigue_rows).to_markdown()
         if fatigue_rows else "尚无足够的用户决定（需要你对通知点批准/拒绝）"),
        ("解读提示",
         "- 采纳率持续走低 = 系统在过度打扰（论文 4.5 授权疲劳）；\n"
         "- 沉默原因集中在 daily_budget = 预算设太紧，集中在 quiet_hours = 时段设太宽；\n"
         "- delivered 长期无回应 = 触达质量差（优先级排序失效）；\n"
         "- 本报告随使用时间积累，14 天个人运行后即成论文二的 OQ5 数据。"),
    ])
    print(f"报告已写入: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
