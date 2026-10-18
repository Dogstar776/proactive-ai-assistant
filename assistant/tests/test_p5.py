"""P5 测试：charter 读写 / 系统状态 / 仪表盘端到端数据链。"""
def test_system_status(client):
    r = client.get("/api/v1/system/status")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "mock"
    assert body["daily_token_budget"] > 0


def test_charter_get_returns_yaml_and_parsed(client):
    r = client.get("/api/v1/charter")
    assert r.status_code == 200
    body = r.json()
    assert "quiet_hours" in body["yaml"]
    assert any(d["name"] == "career" for d in body["parsed"]["domains"])


def test_charter_save_validates_and_reloads(client):
    bad = client.post("/api/v1/charter", json={"yaml": "not: [valid"})
    assert bad.status_code == 400

    empty = client.post("/api/v1/charter", json={"yaml": "version: 1"})
    assert empty.status_code == 400  # 至少一个 domain

    good = client.post(
        "/api/v1/charter",
        json={
            "yaml": (
                "version: 1\nowner: test\n"
                "domains:\n  - name: career\n    weight: 7\n    active: true\n"
            )
        },
    )
    assert good.status_code == 200
    assert good.json()["path"].endswith("charter.yaml")

    # 热重载后门控立即用上新 charter
    r = client.get("/api/v1/charter")
    assert r.json()["parsed"]["domains"][0]["weight"] == 7


def test_dashboard_data_chain(client):
    """仪表盘七个视图的数据链全部可达。"""
    client.post("/api/v1/collectors/run")
    client.post("/api/v1/introspection/run?trigger=dashboard")
    client.post("/api/v1/reminders/run")
    assert client.get("/api/v1/events").status_code == 200
    assert client.get("/api/v1/introspection/reports").status_code == 200
    assert client.get("/api/v1/goals").status_code == 200
    assert client.get("/api/v1/reminders").status_code == 200
    assert client.get("/api/v1/gateway/stats").status_code == 200
    assert client.get("/api/v1/audit").status_code == 200
    assert client.get("/api/v1/consents").status_code == 200
