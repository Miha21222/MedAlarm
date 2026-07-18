import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app


@pytest.mark.asyncio
async def test_api_health_and_readiness():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        readiness = await client.get("/ready")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_pages_origin_cors_preflight():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/sync/bootstrap",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.asyncio
async def test_catalog_status_is_public():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/catalog/status")
    assert response.status_code == 200
    assert response.json()["source_url"].startswith("https://data.gov.ua/")
    assert response.json()["license"] == "CC BY"


@pytest.mark.asyncio
async def test_private_routes_require_bearer_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sync_response = await client.get("/api/v1/sync/bootstrap")
        feedback_response = await client.post("/api/v1/feedback", data={"kind": "rating", "rating": "5"})
    assert sync_response.status_code == 401
    assert feedback_response.status_code == 401
