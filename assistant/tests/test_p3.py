"""P3 测试：缺口检测 / charter / 目标合成 / 深周期 API。"""
from datetime import UTC, datetime, timedelta
from pathlib import Path

from assistant.charter import load_charter
from assistant.goals.repository import GoalRepository, heuristic_priority, new_goal_id
from assistant.goals.templates import DEFAULT_TEMPLATES
from assistant.introspection.detectors import (
    ContradictionDetector,
    DeadlinePrepDetector,
    ThemeClusterDetector,
)
from assistant.introspection.service import IntrospectionService
from assistant.models import ObservedEvent

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


def _ev(**kw) -> ObservedEvent:
    base = dict(source="ics", source_ref="t", consent_id="c", kind="todo", title="t")
    base.update(kw)
    return ObservedEvent(**base)


# ── 缺口检测 ──

def test_deadline_prep_detects_upcoming_without_prep():
    det = DeadlinePrepDetector()
    evs = [_ev(title="视频面试", kind="calendar_event",
               event_time=(NOW + timedelta(days=3)).isoformat())]
    gaps = det.detect(evs, now=NOW)
    assert len(gaps) == 1
    assert gaps[0].kind == "deadline-prep"
    assert gaps[0].score > 0.3


def test_deadline_prep_suppressed_by_related_note():
    det = DeadlinePrepDetector()
    evs = [
        _ev(title="视频面试", kind="calendar_event",
            event_time=(NOW + timedelta(days=3)).isoformat()),
        _ev(title="面试准备笔记", kind="note", source="markdown_notes"),
    ]
    assert det.detect(evs, now=NOW) == []


def test_theme_cluster_detects_repeated_bigram():
    det = ThemeClusterDetector()
    evs = [
        _ev(title="面试安排", kind="calendar_event"),
        _ev(title="面试陈述稿", kind="note", source="markdown_notes"),
    ]
    gaps = det.detect(evs, now=NOW)
    assert any(g.kind == "theme-cluster" and "面试" in g.title for g in gaps)


def test_contradiction_detects_overdue_and_duplicates():
    det = ContradictionDetector()
    evs = [
        _ev(title="过期事项", kind="todo", event_time=(NOW - timedelta(days=2)).isoformat()),
        _ev(title="重复项", source="ics"),
        _ev(title="重复项", source="rss"),
    ]
    gaps = det.detect(evs, now=NOW)
    kinds = {g.kind for g in gaps}
    assert "contradiction" in kinds
    assert any("重复" in g.title for g in gaps)


# ── charter ──

def test_charter_loads_example_and_matches_domain():
    charter = load_charter(Path(__file__).resolve().parent.parent.parent
                           / "docs" / "charter.example.yaml")
    weight, domain = charter.domain_weight("求职：国企数字化运营方向")
    assert domain == "career"
    assert weight > 0
    # 无关文本不攀附域
    assert charter.domain_weight("xyz")[1] is None


# ── 目标合成 ──

def _report_with(gaps):
    from assistant.introspection.service import IntrospectionReport

    return IntrospectionReport(report_id="r1", ts=NOW.isoformat(), trigger="test", gaps=gaps)


def test_templates_synthesize_template_based_goals():
    from assistant.introspection.detectors import Gap

    charter = load_charter(Path(__file__).resolve().parent.parent.parent
                           / "docs" / "charter.example.yaml")
    report = _report_with([
        Gap(kind="deadline-prep", title="「视频面试」临近（3 天）但无相关准备记录",
            detail="d", score=0.8),
        Gap(kind="theme-cluster", title="主题「面试」在 3 个事件中反复出现，尚无梳理记录",
            detail="d", score=0.6),
        Gap(kind="contradiction", title="2 个待办已过截止时间仍无处理记录", detail="d", score=0.5),
    ])
    drafts = [d for t in DEFAULT_TEMPLATES for d in t.match(report.gaps, charter)]
    by_template = {}
    for d in drafts:
        by_template.setdefault(d.template_id, []).append(d)
    assert set(by_template) == {"deadline-prep", "theme-cluster", "contradiction-scan"}
    # 每个草稿都带模板 ID（OQ7 的测量对象）与 [0,1] 分量
    for d in drafts:
        assert d.template_id
        assert 0.0 <= d.info_gain <= 1.0
        assert 0.0 <= d.practical_value <= 1.0
        assert d.risk_level == "R1"  # 只读型认知目标


def test_heuristic_priority_bounded_and_weighted():
    p = heuristic_priority(info_gain=1.0, practical_value=0.0)
    assert 0.5 < p <= 1.0          # 0.6 权重
    assert heuristic_priority(0.0, 1.0) == 0.4
    assert heuristic_priority(5.0, 5.0) == 1.0  # 截断


def test_goal_repository_insert_and_status(conn):
    from assistant.goals.repository import Goal

    repo = GoalRepository(conn)
    g = Goal(goal_id=new_goal_id("r", "t", "x"), title="t", description="d",
             template_id="deadline-prep", priority=0.5)
    assert repo.insert(g) is True
    assert repo.insert(g) is False  # 幂等
    repo.update_status(g.goal_id, "suspended")
    assert repo.list(status="suspended")[0].goal_id == g.goal_id
    assert repo.list(status="active") == []


# ── 深周期 API ──

def test_deep_cycle_api_produces_report_and_goals(client):
    client.post("/api/v1/collectors/run")           # 先有事件
    r = client.post("/api/v1/introspection/run", params={"trigger": "test"})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"].startswith("[B-simulated]")
    assert body["audit"]["total_events"] > 0

    goals = client.get("/api/v1/goals")
    assert goals.status_code == 200
    items = goals.json()["items"]
    assert items, "fixtures 数据应能合成出目标"
    assert all(g["provenance"] == "template-based" for g in items)
    # 队列按优先级降序
    assert [g["priority"] for g in items] == sorted((g["priority"] for g in items), reverse=True)

    # 幂等：再跑一轮不产生重复目标
    n_before = len(items)
    client.post("/api/v1/introspection/run", params={"trigger": "test2"})
    assert len(client.get("/api/v1/goals").json()["items"]) == n_before

    # 生命周期操作
    gid = items[0]["goal_id"]
    st = client.post(f"/api/v1/goals/{gid}/status", params={"status": "suspended"})
    assert st.status_code == 200
    assert all(g["goal_id"] != gid for g in client.get("/api/v1/goals").json()["items"])

    bad = client.post(f"/api/v1/goals/{gid}/status", params={"status": "nope"})
    assert bad.status_code == 400

    reports = client.get("/api/v1/introspection/reports")
    assert reports.status_code == 200
    assert reports.json()["items"][0]["simulated"] == 1


def test_introspection_service_audit_metrics(conn):
    from assistant.events.bus import EventBus
    from assistant.memory.repository import ConsentRepository, EventRepository

    consent = ConsentRepository(conn)
    cid = consent.ensure(collector_id="c", scope="s", description="d", granted_by="t")
    ev = EventRepository(conn)
    ev.upsert(_ev(consent_id=cid, title="过期", kind="todo",
                  event_time=(datetime.now(UTC) - timedelta(days=1)).isoformat()))
    svc = IntrospectionService(events=ev, conn=conn, bus=EventBus())
    report = svc.run_cycle(trigger="test")
    assert report.audit.total_events == 1
    assert report.audit.overdue_open == 1
    assert any(g.kind == "contradiction" for g in report.gaps)
