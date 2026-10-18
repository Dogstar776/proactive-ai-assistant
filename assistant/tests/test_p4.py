"""P4 测试：风险分级 / 四态门控 / 提醒生命周期 / 授权疲劳。"""
from datetime import UTC, datetime, timedelta

from assistant.charter import load_charter
from assistant.events.bus import EventBus
from assistant.gateway.gate import (
    STATE_ACT,
    STATE_ASK,
    STATE_ASSIST,
    STATE_SILENCE,
    Gateway,
    Intervention,
)
from assistant.gateway.reminder_service import ReminderRepository, ReminderService
from assistant.gateway.risk import assess_risk
from assistant.goals.repository import Goal, GoalRepository, new_goal_id
from assistant.introspection.detectors import Gap
from assistant.memory.repository import AuditRepository
from assistant.models import AuditEntry

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)  # 周六中午（非免打扰）


def _charter():
    return load_charter(Path(__file__).resolve().parent.parent.parent
                        / "docs" / "charter.example.yaml")


def _gateway(conn):
    return Gateway(charter=_charter(), audit=AuditRepository(conn))


# ── 风险分级 ──

def test_risk_keyword_escalation():
    assert assess_risk(text="整理面试准备清单").level == "R1"
    r2 = assess_risk(text="草拟一封回复邮件")
    assert r2.level == "R2"
    r3 = assess_risk(text="帮我把这笔订单支付了")
    assert r3.level == "R3"
    assert any("支付" in x for x in r3.reasons)


def test_risk_explicit_goal_level_respected():
    r = assess_risk(goal_risk="R3", text="只读清单")
    assert r.level == "R3"


def test_readonly_template_drafts_stay_r1():
    """回归：模板免责声明不得含高风险词（"不对外发送"曾误触 R3，2026-10-17）。"""
    from assistant.goals.templates import DEFAULT_TEMPLATES

    charter = _charter()
    gaps = [
        Gap(kind="deadline-prep", title="「视频面试」临近（3 天）但无相关准备记录",
            detail="d", score=0.8),
        Gap(kind="theme-cluster", title="主题「面试」在 3 个事件中反复出现，尚无梳理记录",
            detail="d", score=0.6),
        Gap(kind="contradiction", title="2 个待办已过截止时间仍无处理记录", detail="d", score=0.5),
    ]
    for tpl in DEFAULT_TEMPLATES:
        for draft in tpl.match(gaps, charter):
            r = assess_risk(goal_risk=draft.risk_level,
                            text=f"{draft.title} {draft.description}")
            assert r.level == "R1", f"{tpl.template_id} 的措辞触发了 {r.level}: {r.reasons}"


# ── 四态门控 ──

def test_gate_act_for_r1_outside_quiet_hours():
    gw = Gateway(charter=_charter(), audit=_NullAudit())
    d = gw.evaluate(
        Intervention(kind="deadline_nudge", title="t", body="b", cooldown_key="k",
                     text="整理面试准备清单"),
        now=NOW, daily_count_today=0, last_fired={},
    )
    assert d.state == STATE_ACT


def test_gate_silence_in_quiet_hours():
    gw = Gateway(charter=_charter(), audit=_NullAudit())
    # charter 时间是本地时间字面量；构造本地 23:30（周六在示例 charter 免打扰段内）
    late = datetime(2026, 10, 17, 23, 30).astimezone()
    d = gw.evaluate(
        Intervention(kind="deadline_nudge", title="t", body="b", cooldown_key="k"),
        now=late, daily_count_today=0, last_fired={},
    )
    assert d.state == STATE_SILENCE
    assert "quiet_hours" in d.reason


def test_gate_not_quiet_at_local_noon():
    """回归：本地中午不得判免打扰（UTC/本地时区错位 bug，2026-10-17 修复）。"""
    gw = Gateway(charter=_charter(), audit=_NullAudit())
    noon = datetime(2026, 10, 18, 12, 0).astimezone()  # 周日中午（本地）
    d = gw.evaluate(
        Intervention(kind="deadline_nudge", title="t", body="b", cooldown_key="k",
                     text="整理面试准备清单"),
        now=noon, daily_count_today=0, last_fired={},
    )
    assert d.state == STATE_ACT


def test_gate_silence_on_cooldown():
    gw = Gateway(charter=_charter(), audit=_NullAudit())
    d = gw.evaluate(
        Intervention(kind="deadline_nudge", title="t", body="b", cooldown_key="k"),
        now=NOW, daily_count_today=0,
        last_fired={"k": NOW - timedelta(minutes=30)},  # 冷却 120min
    )
    assert d.state == STATE_SILENCE
    assert "cooldown" in d.reason


def test_gate_silence_on_daily_budget():
    gw = Gateway(charter=_charter(), audit=_NullAudit())
    d = gw.evaluate(
        Intervention(kind="deadline_nudge", title="t", body="b", cooldown_key="k"),
        now=NOW, daily_count_today=99, last_fired={},  # 远超 max_proactive_per_day=3
    )
    assert d.state == STATE_SILENCE
    assert "daily_budget" in d.reason


def test_gate_ask_for_r3_with_timeout():
    gw = Gateway(charter=_charter(), audit=_NullAudit())
    d = gw.evaluate(
        Intervention(kind="generic", title="t", body="b", cooldown_key="k",
                     text="把这份材料发送给 HR"),
        now=NOW, daily_count_today=0, last_fired={},
    )
    assert d.state == STATE_ASK
    assert d.expires_at is not None  # 超时默认拒绝的定时器


def test_gate_assist_for_r2():
    gw = Gateway(charter=_charter(), audit=_NullAudit())
    d = gw.evaluate(
        Intervention(kind="generic", title="t", body="b", cooldown_key="k",
                     text="草拟回复提纲"),
        now=NOW, daily_count_today=0, last_fired={},
    )
    assert d.state == STATE_ASSIST
    assert d.expires_at is not None


def test_gate_audits_every_decision_including_silence(conn):
    gw = Gateway(charter=_charter(), audit=AuditRepository(conn))
    late = datetime(2026, 10, 17, 23, 30, tzinfo=UTC)
    gw.evaluate(
        Intervention(kind="deadline_nudge", title="深夜提醒", body="b", cooldown_key="k"),
        now=late, daily_count_today=0, last_fired={},
    )
    audit = AuditRepository(conn).list(action="gate.decision")
    assert audit and audit[0]["status"] == "silence"
    assert "quiet_hours" in audit[0]["detail"]["reason"]


# ── 提醒生命周期 ──

def _make_service(conn, min_priority=0.3):
    charter = _charter()
    return ReminderService(
        repo=ReminderRepository(conn),
        gateway=Gateway(charter=charter, audit=AuditRepository(conn)),
        goals=GoalRepository(conn),
        charter=charter,
        bus=EventBus(),
        audit=AuditRepository(conn),
        min_priority=min_priority,
    )


def _add_goal(conn, **kw):
    repo = GoalRepository(conn)
    base = dict(goal_id=new_goal_id("t", kw.get("title", "x")), title="x",
                description="整理面试准备清单", template_id="deadline-prep",
                priority=0.6, risk_level="R1")
    base.update(kw)
    g = Goal(**base)
    repo.insert(g)
    return g


def test_reminder_cycle_delivers_r1_and_records_silence(conn):
    svc = _make_service(conn)
    _add_goal(conn, title="为「视频面试」做截止前准备")
    result = svc.run_cycle(now=NOW)
    assert result["evaluated"] == 1
    assert result["act"] == 1
    delivered = svc.repo.list(status="delivered")
    assert delivered and delivered[0].state == "act"


def test_reminder_low_priority_filtered(conn):
    svc = _make_service(conn, min_priority=0.9)
    _add_goal(conn, title="低优先级目标", priority=0.2)
    result = svc.run_cycle(now=NOW)
    assert result["evaluated"] == 0


def test_reminder_pending_requires_human_and_expires(conn):
    svc = _make_service(conn)
    _add_goal(conn, title="草拟对外材料", risk_level="R3")
    result = svc.run_cycle(now=NOW)
    assert result["ask"] == 1
    pending = svc.repo.list(status="pending")
    assert pending and pending[0].state == "ask"

    # 批准 → 触达
    r = svc.approve(pending[0].reminder_id)
    assert r.status == "approved"

    # 超时清扫：另一个 pending 超过 24h → expired
    _add_goal(conn, title="另一件高风险事", risk_level="R3")
    svc.run_cycle(now=NOW)
    later = NOW + timedelta(hours=25)
    result2 = svc.run_cycle(now=later)
    assert result2["expired"] >= 1
    expired = [x for x in svc.repo.list(status="expired")]
    assert expired


def test_reminder_reject_lifecycle(conn):
    svc = _make_service(conn)
    _add_goal(conn, title="待确认事项", risk_level="R2")
    svc.run_cycle(now=NOW)
    pending = svc.repo.list(status="pending")
    assert pending
    svc.reject(pending[0].reminder_id)
    assert not svc.repo.list(status="pending")


def test_reminder_cooldown_prevents_second_cycle(conn):
    svc = _make_service(conn)
    _add_goal(conn, title="冷却测试")
    r1 = svc.run_cycle(now=NOW)
    r2 = svc.run_cycle(now=NOW + timedelta(minutes=30))  # 冷却 120min 内
    assert r1["act"] == 1
    assert r2["silence"] == 1


def test_fatigue_stats(conn):
    svc = _make_service(conn)
    _add_goal(conn, title="高风险A", risk_level="R3")
    _add_goal(conn, title="高风险B", risk_level="R3")
    svc.run_cycle(now=NOW)
    pending = svc.repo.list(status="pending")
    svc.approve(pending[0].reminder_id)
    svc.reject(pending[1].reminder_id)
    stats = svc.fatigue_stats()
    assert stats["ask_total"] >= 2
    assert stats["approval_rate"] is not None


# ── API ──

def test_reminder_api_flow(client):
    client.post("/api/v1/collectors/run")
    client.post("/api/v1/introspection/run")
    r = client.post("/api/v1/reminders/run")
    assert r.status_code == 200
    body = r.json()["results"]
    assert body["evaluated"] > 0

    stats = client.get("/api/v1/gateway/stats")
    assert stats.status_code == 200
    assert "fatigue" in stats.json()

    audit = client.get("/api/v1/audit", params={"action": "gate.decision"})
    assert audit.status_code == 200
    assert audit.json()["items"], "每次门控判决都必须留痕"


class _NullAudit:
    """门控单测用的空审计（不落库）。"""

    def append(self, entry: AuditEntry) -> None:
        pass


from pathlib import Path  # noqa: E402  （置于文件末尾以避免影响 fixtures 导入顺序）
