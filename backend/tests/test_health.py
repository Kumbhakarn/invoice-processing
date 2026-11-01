"""Health endpoint tests."""

from fastapi.testclient import TestClient

from docextract.main import app


def test_health_check_returns_ok() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
