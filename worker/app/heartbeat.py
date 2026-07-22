"""Worker heartbeat persistence (TP-0805 / TP-1703 fix).

Stores and refreshes worker heartbeat records in PostgreSQL using a
session factory so that each operation opens its own short-lived session
while the heartbeat record ID persists in the instance for the worker's
lifetime.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class WorkerHeartbeat:
    """Manages heartbeat records for one worker instance.

    Accepts an ``async_sessionmaker`` rather than a single session so that
    ``initialize``, ``refresh``, and ``finalize`` each get their own
    short-lived database session.  The heartbeat record ID is stored on
    the instance and reused across calls.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_id: str,
    ) -> None:
        self._factory = session_factory
        self._worker_id = worker_id
        self._started_at = datetime.now(timezone.utc)
        self._heartbeat_id: uuid.UUID | None = None

    async def initialize(self) -> None:
        """Create the initial heartbeat record."""
        now = datetime.now(timezone.utc)
        async with self._factory() as session:
            result = await session.execute(
                text(
                    "INSERT INTO worker_heartbeats "
                    "(worker_id, started_at, last_seen_at, status) "
                    "VALUES (:wid, :started, :now, 'RUNNING') "
                    "RETURNING id"
                ),
                {
                    "wid": self._worker_id,
                    "started": self._started_at,
                    "now": now,
                },
            )
            self._heartbeat_id = result.scalar_one()
            await session.commit()

    async def refresh(self) -> None:
        """Update ``last_seen_at`` for the current heartbeat record."""
        if self._heartbeat_id is None:
            return
        now = datetime.now(timezone.utc)
        async with self._factory() as session:
            await session.execute(
                text("UPDATE worker_heartbeats SET last_seen_at = :now WHERE id = :hid"),
                {"now": now, "hid": self._heartbeat_id},
            )
            await session.commit()

    async def finalize(self, status: str = "STOPPED") -> None:
        """Set the final status and update ``last_seen_at``."""
        if self._heartbeat_id is None:
            return
        now = datetime.now(timezone.utc)
        async with self._factory() as session:
            await session.execute(
                text(
                    "UPDATE worker_heartbeats SET "
                    "status = :st, last_seen_at = :now "
                    "WHERE id = :hid"
                ),
                {"st": status, "now": now, "hid": self._heartbeat_id},
            )
            await session.commit()
