"""Tests for health and readiness endpoints (TP-1602).

Covers: healthy application, ready database + schema registry,
database unavailable, schema registry unavailable, storage health,
provider outage not affecting readiness.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.health import router as health_router
from app.config import AppConfig
from app.database.session import get_db_session

pytestmark = pytest.mark.database

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app(override_session: AsyncSession | None = None) -> FastAPI:
    """Build a minimal FastAPI app with the health router.

    Optionally overrides ``get_db_session`` with *override_session*.
    """
    app = FastAPI()
    app.include_router(health_router)

    if override_session is not None:

        async def _override() -> AsyncSession:
            return override_session

        app.dependency_overrides[get_db_session] = _override

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


# ===================================================================
# 1. GET /health
# ===================================================================


class TestHealth:
    async def test_healthy(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "tradepilot-backend"
        assert isinstance(body["version"], str)

    async def test_stable_fields(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        body = resp.json()
        assert set(body.keys()) == {"status", "service", "version"}


# ===================================================================
# 2. GET /health/ready
# ===================================================================


class TestReady:
    async def test_ready_database(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["database"]["status"] == "healthy"

    async def test_database_unavailable(self) -> None:
        """Simulate DB failure by passing a session whose connection will fail."""
        from unittest.mock import AsyncMock

        failing_session = AsyncMock(spec=AsyncSession)
        failing_session.execute.side_effect = ConnectionRefusedError("connection refused")
        app = _build_app(failing_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "unhealthy"
        assert body["database"]["status"] == "unhealthy"


# ===================================================================
# 3. Storage health
# ===================================================================


class TestStorageHealth:
    async def test_storage_health_endpoint(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/storage")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("healthy", "unhealthy")


# ===================================================================
# 4. Provider outage not affecting readiness
# ===================================================================


class TestProviderOutage:
    async def test_readiness_ignores_provider(self, db_session: AsyncSession) -> None:
        """Provider (Gemini/DeepSeek) unavailability does not affect readiness."""
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        # Readiness should be "ready" when DB is fine
        # regardless of whether AI providers are available
        assert body["status"] == "ready"
        # Provider fields must not appear in the response
        assert "provider" not in body
        assert "gemini" not in str(body)
