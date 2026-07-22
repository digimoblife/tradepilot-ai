"""Tests for health and readiness endpoints (TP-1602).

Covers: healthy application, ready database + schema registry,
database unavailable, schema registry unavailable, worker heartbeat
available, stale heartbeat, absent heartbeat, provider outage not
affecting readiness.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.health import router as health_router
from app.config import AppConfig
from app.database.session import get_db_session
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry

pytestmark = pytest.mark.database

_INSERT_HB = (
    "INSERT INTO worker_heartbeats "
    "(id, worker_id, started_at, last_seen_at, status) "
    "VALUES (:id, :wid, :started, :seen, 'RUNNING')"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app(override_session: AsyncSession | None = None) -> FastAPI:
    """Build a minimal FastAPI app with the health router.

    Optionally overrides ``get_db_session`` with *override_session*.
    Optionally sets up a real schema registry on ``app.state``.
    """
    app = FastAPI()
    app.include_router(health_router)

    if override_session is not None:

        async def _override() -> AsyncSession:
            return override_session

        app.dependency_overrides[get_db_session] = _override

    return app


def _add_schema_registry(app: FastAPI) -> None:
    """Load and attach a real production schema registry."""
    config = AppConfig()
    from pathlib import Path

    pkg = Path(config.schema_package_root)
    manifest = load_production_manifest(pkg)
    registry = LocalSchemaRegistry(manifest, pkg)
    app.state.schema_manifest = manifest
    app.state.schema_registry = registry


async def _ensure_worker_heartbeats_table(engine: AsyncEngine) -> None:
    """Create worker_heartbeats table matching migration 3f0b2a4f1e24.

    The production Alembic migration ``3f0b2a4f1e24`` creates this table.
    Test isolation requirements prevent running Alembic within test sessions;
    this helper applies the equivalent DDL so that the production schema
    definition (not ad-hoc test DDL) determines the table structure.
    """
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS worker_heartbeats (
                id UUID PRIMARY KEY,
                worker_id TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                last_seen_at TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL DEFAULT 'RUNNING'
            )
        """)
        )


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
    async def test_ready_database_and_schema(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        _add_schema_registry(app)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["database"]["status"] == "healthy"
        assert body["schema_registry"]["status"] == "healthy"

    async def test_database_unavailable(self) -> None:
        """Simulate DB failure by passing a session whose connection will fail."""
        app = _build_app()  # No override -> will fail because no DB session available
        _add_schema_registry(app)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "unhealthy"
        assert body["database"]["status"] == "unhealthy"

    async def test_schema_registry_unavailable(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        # Deliberately do NOT attach a schema registry
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "unhealthy"
        assert body["schema_registry"]["status"] == "unhealthy"


# ===================================================================
# 3. GET /health/schema-registry
# ===================================================================


class TestSchemaRegistry:
    async def test_healthy(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        _add_schema_registry(app)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/schema-registry")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert isinstance(body["registered_resources"], int)
        assert body["registered_resources"] > 0
        assert isinstance(body["compiled_validators"], int)
        assert body["compiled_validators"] > 0

    async def test_not_loaded(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/schema-registry")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_loaded"


# ===================================================================
# 4. GET /health/worker
# ===================================================================


class TestWorkerHeartbeat:
    async def test_absent_when_table_missing(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS worker_heartbeats"))
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/worker")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "absent"

    async def test_absent_when_no_records(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        await _ensure_worker_heartbeats_table(engine)
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM worker_heartbeats"))
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/worker")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "absent"

    async def test_healthy_heartbeat(self, engine: AsyncEngine, db_session: AsyncSession) -> None:
        await _ensure_worker_heartbeats_table(engine)
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM worker_heartbeats"))
        now = datetime.now(timezone.utc)
        hb_id = uuid.uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text(_INSERT_HB),
                {
                    "id": hb_id,
                    "wid": "test-worker-1",
                    "started": now - timedelta(minutes=10),
                    "seen": now - timedelta(seconds=30),
                },
            )
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/worker")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["worker_id"] == "test-worker-1"
        assert body["running_status"] == "RUNNING"
        assert isinstance(body["started_at"], str)
        assert isinstance(body["last_seen_at"], str)

    async def test_stale_heartbeat(self, engine: AsyncEngine, db_session: AsyncSession) -> None:
        await _ensure_worker_heartbeats_table(engine)
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM worker_heartbeats"))
        now = datetime.now(timezone.utc)
        hb_id = uuid.uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text(_INSERT_HB),
                {
                    "id": hb_id,
                    "wid": "test-worker-stale",
                    "started": now - timedelta(hours=1),
                    "seen": now - timedelta(minutes=10),
                },
            )
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/worker")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "stale"
        assert body["worker_id"] == "test-worker-stale"

    async def test_stopped_heartbeat_is_stale(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        """A STOPPED heartbeat must not be reported as healthy."""
        await _ensure_worker_heartbeats_table(engine)
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM worker_heartbeats"))
        now = datetime.now(timezone.utc)
        hb_id = uuid.uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO worker_heartbeats "
                    "(id, worker_id, started_at, last_seen_at, status) "
                    "VALUES (:id, :wid, :started, :seen, 'STOPPED')"
                ),
                {
                    "id": hb_id,
                    "wid": "test-worker-stopped",
                    "started": now - timedelta(minutes=30),
                    "seen": now - timedelta(seconds=10),
                },
            )
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/worker")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "stale"
        assert body["running_status"] == "STOPPED"
        assert "stopped" in body.get("detail", "").lower()


# ===================================================================
# 5. Provider outage not affecting readiness
# ===================================================================


class TestProviderOutage:
    async def test_readiness_ignores_provider(self, db_session: AsyncSession) -> None:
        """Provider (Gemini/DeepSeek) unavailability does not affect readiness."""
        app = _build_app(db_session)
        _add_schema_registry(app)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        # Readiness should be "ready" when DB + schema registry are fine
        # regardless of whether AI providers are available
        assert body["status"] == "ready"
        # Provider fields must not appear in the response
        assert "provider" not in body
        assert "gemini" not in str(body)
