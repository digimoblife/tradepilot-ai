"""Archive Session Action Service (TP-0507).

Archives a terminal or cancelled Trade Session.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context_summary import ContextSummary
from app.models.enums import ActionType, SessionEventType, TradeSessionStatus
from app.models.session_event import SessionEvent
from app.models.trade_action import TradeAction
from app.repositories.trade_session import TradeSessionRepository

_ELIGIBLE_FOR_ARCHIVE = frozenset(
    {
        TradeSessionStatus.CANCELLED,
        TradeSessionStatus.CLOSED_TAKE_PROFIT,
        TradeSessionStatus.CLOSED_STOP_LOSS,
        TradeSessionStatus.CLOSED_MANUAL,
    }
)


class ArchiveSessionError(Exception):
    code = "ARCHIVE_SESSION_ERROR"


class ArchiveSessionInvalidStateError(ArchiveSessionError):
    code = "ARCHIVE_SESSION_INVALID_STATE"


class ArchiveSessionNotFoundError(ArchiveSessionError):
    code = "ARCHIVE_SESSION_NOT_FOUND_OR_NOT_OWNED"


@dataclass(frozen=True, slots=True)
class ArchiveSessionResult:
    session_id: uuid.UUID
    action: TradeAction
    session_status: TradeSessionStatus


class ArchiveSessionActionService:
    """Archive an eligible (terminal or cancelled) Trade Session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TradeSessionRepository(session)

    async def confirm(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        idempotency_key: str,
        archived_at: datetime,
        note: str | None = None,
    ) -> ArchiveSessionResult:
        ts = await self._repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise ArchiveSessionNotFoundError(
                f"Session {session_id} not found for user {owner_id}"
            )

        # Idempotency
        existing = (
            (
                await self._session.execute(
                    select(TradeAction).where(
                        TradeAction.session_id == session_id,
                        TradeAction.idempotency_key == idempotency_key,
                    )
                )
            )
            .unique()
            .scalar_one_or_none()
        )
        if existing is not None:
            return ArchiveSessionResult(
                session_id=session_id,
                action=existing,
                session_status=TradeSessionStatus.ARCHIVED,
            )

        # Validate state
        if ts.lifecycle_status not in _ELIGIBLE_FOR_ARCHIVE:
            raise ArchiveSessionInvalidStateError(
                f"Cannot archive: session is {ts.lifecycle_status.value}. "
                f"Only CANCELLED, CLOSED_TAKE_PROFIT, CLOSED_STOP_LOSS, "
                f"or CLOSED_MANUAL can be archived."
            )

        # Create action
        action = TradeAction(
            session_id=session_id,
            action_type=ActionType.SESSION_ARCHIVED,
            confirmed_at=archived_at,
            idempotency_key=idempotency_key,
            note=note,
        )
        self._session.add(action)

        # Update session
        ts.lifecycle_status = TradeSessionStatus.ARCHIVED
        ts.stable_status = TradeSessionStatus.ARCHIVED

        # Create event
        event = SessionEvent(
            session_id=session_id,
            event_type=SessionEventType.SESSION_ARCHIVED,
            occurred_at=archived_at,
            related_action_id=action.id,
            compact_summary="Session archived",
        )
        self._session.add(event)

        # Mark Context Summary stale
        await self._session.execute(
            update(ContextSummary)
            .where(ContextSummary.session_id == session_id, ContextSummary.is_stale == False)  # noqa: E712
            .values(is_stale=True)
        )

        await self._session.flush()

        return ArchiveSessionResult(
            session_id=session_id,
            action=action,
            session_status=TradeSessionStatus.ARCHIVED,
        )
