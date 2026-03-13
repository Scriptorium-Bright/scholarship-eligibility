from fastapi.testclient import TestClient

from app.main import create_app


def test_ready_endpoint_reports_database_health(monkeypatch):
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
