from fastapi.testclient import TestClient

from app.api.main import app


def test_api_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sync_requires_bearer_authentication():
    with TestClient(app) as client:
        response = client.get("/api/v1/sync/bootstrap")
    assert response.status_code == 401
