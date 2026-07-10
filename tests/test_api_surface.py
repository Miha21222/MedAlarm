from fastapi.testclient import TestClient

from app.api.main import app


def test_api_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_readiness_checks_database():
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_pages_origin_cors_preflight():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/sync/bootstrap",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_sync_requires_bearer_authentication():
    with TestClient(app) as client:
        response = client.get("/api/v1/sync/bootstrap")
    assert response.status_code == 401


def test_feedback_requires_bearer_authentication():
    with TestClient(app) as client:
        response = client.post("/api/v1/feedback", data={"kind": "rating", "rating": "5"})
    assert response.status_code == 401
