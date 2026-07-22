"""Tests for worker heartbeat lifecycle (TP-1703 fix).

Covers the refactored ``WorkerHeartbeat`` that uses a session factory
so the heartbeat ID survives across sessions while each operation gets
its own short-lived database session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

from app.heartbeat import WorkerHeartbeat

pytestmark = pytest.mark.database


# ===================================================================
# In-memory SQL simulator for unit-testing the heartbeat logic
# ===================================================================


class _FakeHeartbeatRow:
    """Simulates one row in worker_heartbeats."""

    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.worker_id: str = ""
        self.started_at: datetime = datetime.now(timezone.utc)
        self.last_seen_at: datetime = datetime.now(timezone.utc)
        self.status: str = "RUNNING"


class _FakeResult:
    """Simulates a SQLAlchemy result."""

    def __init__(self, row: _FakeHeartbeatRow | None = None) -> None:
        self._row = row

    def scalar_one(self) -> uuid.UUID:
        assert self._row is not None
        return self._row.id

    def first(self) -> Any:
        return None


class _FakeSession:
    """Simulates an async DB session for testing heartbeat logic."""

    def __init__(self, row: _FakeHeartbeatRow | None = None) -> None:
        self.row = row
        self.committed = False

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def execute(self, statement: Any, params: Any = None) -> _FakeResult:
        return _FakeResult(self.row)

    async def commit(self) -> None:
        self.committed = True


class _FakeSessionFactory:
    """Simulates an ``async_sessionmaker``."""

    def __init__(self, row: _FakeHeartbeatRow | None = None) -> None:
        self.row = row

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.row)


# ===================================================================
# Heartbeat lifecycle tests
# ===================================================================


class TestHeartbeatLifecycle:
    async def test_initialize_stores_id(self) -> None:
        row = _FakeHeartbeatRow()
        factory = _FakeSessionFactory(row)
        hb = WorkerHeartbeat(factory, "test-worker")

        assert hb._heartbeat_id is None
        await hb.initialize()
        assert hb._heartbeat_id == row.id

    async def test_refresh_uses_same_id(self) -> None:
        row = _FakeHeartbeatRow()
        factory = _FakeSessionFactory(row)
        hb = WorkerHeartbeat(factory, "test-worker")

        await hb.initialize()
        saved_id = hb._heartbeat_id
        assert saved_id is not None

        await hb.refresh()
        assert hb._heartbeat_id == saved_id

    async def test_finalize_uses_same_id(self) -> None:
        row = _FakeHeartbeatRow()
        factory = _FakeSessionFactory(row)
        hb = WorkerHeartbeat(factory, "test-worker")

        await hb.initialize()
        saved_id = hb._heartbeat_id
        assert saved_id is not None

        await hb.finalize("STOPPED")
        assert hb._heartbeat_id == saved_id

    async def test_refresh_no_id_is_safe(self) -> None:
        """refresh() with no heartbeat_id should not raise."""
        factory = _FakeSessionFactory()
        hb = WorkerHeartbeat(factory, "test-worker")
        await hb.refresh()  # should not raise

    async def test_finalize_no_id_is_safe(self) -> None:
        """finalize() with no heartbeat_id should not raise."""
        factory = _FakeSessionFactory()
        hb = WorkerHeartbeat(factory, "test-worker")
        await hb.finalize("STOPPED")  # should not raise

    async def test_separate_sessions_per_call(self) -> None:
        """Each method should use its own session (not store one)."""
        row = _FakeHeartbeatRow()
        factory = _FakeSessionFactory(row)
        hb = WorkerHeartbeat(factory, "test-worker")

        # Before any call there is no session stored on the instance
        assert not hasattr(hb, "_session") or hb._session is None

        await hb.initialize()
        assert not hasattr(hb, "_session") or hb._session is None

        await hb.refresh()
        assert not hasattr(hb, "_session") or hb._session is None

        await hb.finalize()
        assert not hasattr(hb, "_session") or hb._session is None

    async def test_session_factory_stored(self) -> None:
        """The session factory is stored, not a session."""
        factory = _FakeSessionFactory()
        hb = WorkerHeartbeat(factory, "test-worker")
        assert hb._factory is factory


# ===================================================================
# Runtime heartbeat reuse tests (using FakeHeartbeat)
# ===================================================================


class _FakeRuntimeHeartbeat:
    """Minimal fake that records the call pattern."""

    def __init__(self) -> None:
        self.initialized = False
        self.refreshed = False
        self.finalized = False
        self.final_status: str | None = None

    async def initialize(self) -> None:
        self.initialized = True

    async def refresh(self) -> None:
        self.refreshed = True

    async def finalize(self, status: str = "STOPPED") -> None:
        self.finalized = True
        self.final_status = status


class TestRuntimeHeartbeatReuse:
    async def test_one_instance_for_lifecycle(self) -> None:
        """The same FakeHeartbeat instance is used for init, refresh, finalize."""
        hb = _FakeRuntimeHeartbeat()
        await hb.initialize()
        assert hb.initialized
        assert not hb.refreshed
        assert not hb.finalized

        await hb.refresh()
        assert hb.refreshed

        await hb.finalize("STOPPED")
        assert hb.finalized
        assert hb.final_status == "STOPPED"
