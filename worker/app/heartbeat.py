"""Worker heartbeat persistence (TP-0805).

Stores and refreshes worker heartbeat records in PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class WorkerHeartbeat:
    """Manages heartbeat records for one worker instance."""

    def __init__(self, session: AsyncSession, worker_id: str) -> None:
        self._session = session
        self._worker_id = worker_id
        self._started_at = datetime.now(timezone.utc)
        self._heartbeat_id: uuid.UUID | None = None

    async def initialize(self) -> None:
        """Create the initial heartbeat record."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
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
        await self._session.commit()

    async def refresh(self) -> None:
        """Update last_seen_at for the current heartbeat record."""
        now = datetime.now(timezone.utc)
        if self._heartbeat_id is not None:
            await self._session.execute(
                text("UPDATE worker_heartbeats SET last_seen_at = :now WHERE id = :hid"),
                {"now": now, "hid": self._heartbeat_id},
            )
            await self._session.commit()

    async def finalize(self, status: str = "STOPPED") -> None:
        """Set the final status and update last_seen_at."""
        now = datetime.now(timezone.utc)
        if self._heartbeat_id is not None:
            await self._session.execute(
                text(
                    "UPDATE worker_heartbeats SET "
                    "status = :st, last_seen_at = :now "
                    "WHERE id = :hid"
                ),
                {"st": status, "now": now, "hid": self._heartbeat_id},
            )
            await self._session.commit()
