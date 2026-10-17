"""API 冒烟测试：健康检查、事件查询、采集触发、审计、SSE 统计。"""
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_after_migrations(client):
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["schema_version"] >= 1


def test_run_cycle_then_list_events(client):
    # 触发一次轻观测周期（fixtures 已通过 env 配置）
    r = client.post("/api/v1/collectors/run")
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 3
    assert all(x["status"] == "ok" for x in results), results
    inserted = sum(x["items_inserted"] for x in results)
    assert inserted > 0

    ev = client.get("/api/v1/events")
    assert ev.status_code == 200
    body = ev.json()
    assert body["stats"]["total"] == inserted
    assert set(body["stats"]["by_source"]) == {"ics", "markdown_notes", "rss"}

    # 幂等：再跑一次，inserted 全为 0
    r2 = client.post("/api/v1/collectors/run")
    assert sum(x["items_inserted"] for x in r2.json()["results"]) == 0


def test_events_filters(client):
    client.post("/api/v1/collectors/run")
    ev = client.get("/api/v1/events", params={"kind": "todo"})
    assert all(i["kind"] == "todo" for i in ev.json()["items"])


def test_audit_and_consents(client):
    client.post("/api/v1/collectors/run")
    audit = client.get("/api/v1/audit")
    assert audit.status_code == 200
    assert any(a["action"] == "collector.run" for a in audit.json()["items"])

    consents = client.get("/api/v1/consents")
    assert len(consents.json()["items"]) == 3
    cid = consents.json()["items"][0]["consent_id"]

    revoked = client.post(f"/api/v1/consents/{cid}/revoke")
    assert revoked.status_code == 200

    # 撤回后该连接器被跳过
    r = client.post("/api/v1/collectors/run")
    assert any(x["status"] == "skipped_revoked" for x in r.json()["results"])


def test_collectors_endpoint(client):
    r = client.get("/api/v1/collectors")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 3
    assert body["bus"]["subscribers"] >= 0


def test_error_shape_is_normalized(client):
    """4xx 错误返回规范化结构，不含堆栈。"""
    r = client.get("/api/v1/events", params={"limit": 0})
    assert r.status_code == 422  # FastAPI 参数校验
    r2 = client.post("/api/v1/collectors/run", params={"collector_id": "nope"})
    assert r2.status_code == 404
    body = r2.json()
    assert body["code"] == "not_found"
    assert "request_id" in body
