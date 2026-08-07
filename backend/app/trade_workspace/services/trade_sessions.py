from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


class ArchiveError(Exception):
    code = "ARCHIVE_FAILED"
    status_code = 422


class ArchiveSessionNotFoundError(ArchiveError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class ArchiveNotAllowedError(ArchiveError):
    code = "ARCHIVE_NOT_ALLOWED"
    status_code = 409


class ArchiveAlreadyArchivedError(ArchiveError):
    code = "SESSION_ALREADY_ARCHIVED"
    status_code = 409


class RestoreNotAllowedError(ArchiveError):
    code = "RESTORE_NOT_ALLOWED"
    status_code = 409


class RestoreNotArchivedError(ArchiveError):
    code = "SESSION_NOT_ARCHIVED"
    status_code = 409


class ArchivePersistenceError(ArchiveError):
    code = "ARCHIVE_PERSISTENCE_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    session_id: uuid.UUID
    session_status: TradeSessionV2Status
    archived_at: datetime | None


class RebuildTradeSessionService:
    """Persistence operations for the rebuild-owned session API."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        ticker: str,
        company_name: str,
        note: str | None,
    ) -> TradeSessionV2:
        normalized_ticker = ticker.strip().upper()
        normalized_company_name = company_name.strip()
        if not normalized_ticker or not normalized_company_name:
            raise ValueError("Ticker and company name must not be blank")

        trade_session = TradeSessionV2(
            user_id=user_id,
            ticker=normalized_ticker,
            company_name=normalized_company_name,
            note=note,
            status=TradeSessionV2Status.DRAFT,
            closed_at=None,
        )
        self._session.add(trade_session)
        await self._session.flush()
        return trade_session

    async def list_owned(self, *, user_id: uuid.UUID) -> list[TradeSessionV2]:
        result = await self._session.scalars(
            select(TradeSessionV2)
            .where(
                TradeSessionV2.user_id == user_id,
                TradeSessionV2.archived_at.is_(None),
            )
            .order_by(TradeSessionV2.created_at.desc(), TradeSessionV2.id.desc())
        )
        return list(result.all())

    async def list_owned_archived(self, *, user_id: uuid.UUID) -> list[TradeSessionV2]:
        result = await self._session.scalars(
            select(TradeSessionV2)
            .where(
                TradeSessionV2.user_id == user_id,
                TradeSessionV2.archived_at.is_not(None),
            )
            .order_by(TradeSessionV2.created_at.desc(), TradeSessionV2.id.desc())
        )
        return list(result.all())

    async def get_owned(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TradeSessionV2 | None:
        return await self._session.scalar(
            select(TradeSessionV2).where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
        )

    async def archive(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ArchiveResult:
        await self._lock(session_id)
        trade_session = await self._load_owned_for_update(user_id, session_id)
        if trade_session is None:
            raise ArchiveSessionNotFoundError("Rebuild session was not found")
        if trade_session.status not in {
            TradeSessionV2Status.CLOSED,
            TradeSessionV2Status.CLOSED_SKIPPED,
        }:
            raise ArchiveNotAllowedError(
                "Only CLOSED and CLOSED_SKIPPED sessions can be archived"
            )
        if trade_session.archived_at is not None:
            raise ArchiveAlreadyArchivedError("Rebuild session is already archived")

        trade_session.archived_at = datetime.now(timezone.utc)
        try:
            await self._session.flush()
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise ArchivePersistenceError("Rebuild session could not be archived") from exc

        return ArchiveResult(
            session_id=trade_session.id,
            session_status=trade_session.status,
            archived_at=trade_session.archived_at,
        )

    async def restore(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ArchiveResult:
        await self._lock(session_id)
        trade_session = await self._load_owned_for_update(user_id, session_id)
        if trade_session is None:
            raise ArchiveSessionNotFoundError("Rebuild session was not found")
        if trade_session.status not in {
            TradeSessionV2Status.CLOSED,
            TradeSessionV2Status.CLOSED_SKIPPED,
        }:
            raise RestoreNotAllowedError(
                "Only terminal sessions can be restored"
            )
        if trade_session.archived_at is None:
            raise RestoreNotArchivedError("Rebuild session is not archived")

        trade_session.archived_at = None
        try:
            await self._session.flush()
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise ArchivePersistenceError("Rebuild session could not be restored") from exc

        return ArchiveResult(
            session_id=trade_session.id,
            session_status=trade_session.status,
            archived_at=trade_session.archived_at,
        )

    async def _load_owned_for_update(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TradeSessionV2 | None:
        return await self._session.scalar(
            select(TradeSessionV2)
            .where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
            .with_for_update()
        )

    async def _lock(self, session_id: uuid.UUID) -> None:
        await self._session.execute(
            select(func.pg_advisory_xact_lock(_session_lock_key(session_id)))
        )


def _session_lock_key(session_id: uuid.UUID) -> int:
    return int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
