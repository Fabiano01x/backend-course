import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app, create_app


pytestmark = pytest.mark.anyio


async def test_allows_configured_origin_and_adds_security_headers() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/health", headers={"Origin": "http://localhost:5173"}
        )

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "strict-transport-security" not in response.headers


async def test_denies_unknown_origin() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/health", headers={"Origin": "https://attacker.example"}
        )
    assert "access-control-allow-origin" not in response.headers


async def test_handles_preflight_with_security_headers() -> None:
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options("/books", headers=headers)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "PUT" in response.headers["access-control-allow-methods"]
    assert "DELETE" in response.headers["access-control-allow-methods"]
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_hsts_requires_production_and_https() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        https_enabled=True,
        allowed_origins=["https://library.example"],
    )
    production_app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=production_app), base_url="https://test"
    ) as client:
        response = await client.get("/health")
    assert response.headers["strict-transport-security"].startswith("max-age=")


async def test_production_without_https_does_not_add_hsts() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        https_enabled=False,
        allowed_origins=["https://library.example"],
    )
    production_app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=production_app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert "strict-transport-security" not in response.headers


async def test_docs_remain_available_without_generic_csp() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        docs = await client.get("/docs")
        redoc = await client.get("/redoc")
    assert docs.status_code == 200
    assert redoc.status_code == 200
    assert "content-security-policy" not in docs.headers
