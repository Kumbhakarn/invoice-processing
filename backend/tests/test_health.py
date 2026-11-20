"""Health endpoint tests."""

from fastapi.testclient import TestClient

from docextract.main import app


def test_health_check_returns_ok() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database_not_ready_when_unconfigured() -> None:
    response = TestClient(app).get("/api/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}


def test_readiness_openapi_documents_success_and_database_failure() -> None:
    responses = TestClient(app).get("/openapi.json").json()["paths"]["/api/ready"]["get"][
        "responses"
    ]

    assert "200" in responses
    assert "503" in responses
