"""Cancel Session Action Service (TP-0507).

Cancels a Trade Session before a real position is opened.
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

_ELIGIBLE_FOR_CANCEL = frozenset(
    {
        TradeSessionStatus.DRAFT,
        TradeSessionStatus.READY_FOR_ANALYSIS,
        TradeSessionStatus.ANALYZING,
        TradeSessionStatus.WATCHING,
    }
)


class CancelSessionError(Exception):
    code = "CANCEL_SESSION_ERROR"


class CancelSessionInvalidStateError(CancelSessionError):
    code = "CANCEL_SESSION_INVALID_STATE"


class CancelSessionNotFoundError(CancelSessionError):
    code = "CANCEL_SESSION_NOT_FOUND_OR_NOT_OWNED"


@dataclass(frozen=True, slots=True)
class CancelSessionResult:
    session_id: uuid.UUID
    action: TradeAction
    session_status: TradeSessionStatus


class CancelSessionActionService:
    """Cancel a Trade Session before a position is opened."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TradeSessionRepository(session)

    async def confirm(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        idempotency_key: str,
        cancelled_at: datetime,
        reason: str | None = None,
        note: str | None = None,
    ) -> CancelSessionResult:
        ts = await self._repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise CancelSessionNotFoundError(f"Session {session_id} not found for user {owner_id}")

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
            return CancelSessionResult(
                session_id=session_id,
                action=existing,
                session_status=TradeSessionStatus.CANCELLED,
            )

        # Validate state
        if ts.lifecycle_status not in _ELIGIBLE_FOR_CANCEL:
            raise CancelSessionInvalidStateError(
                f"Cannot cancel: session is {ts.lifecycle_status.value}. "
                f"Only DRAFT, READY_FOR_ANALYSIS, ANALYZING, or WATCHING can be cancelled."
            )

        # Create action
        action = TradeAction(
            session_id=session_id,
            action_type=ActionType.SESSION_CANCELLED,
            confirmed_at=cancelled_at,
            idempotency_key=idempotency_key,
            note=note or reason,
            payload={"reason": reason},
        )
        self._session.add(action)

        # Update session
        ts.lifecycle_status = TradeSessionStatus.CANCELLED
        ts.stable_status = TradeSessionStatus.CANCELLED

        # Create event
        event = SessionEvent(
            session_id=session_id,
            event_type=SessionEventType.NOTE_ADDED,
            occurred_at=cancelled_at,
            related_action_id=action.id,
            compact_summary=f"Session cancelled: {reason or 'no reason given'}",
        )
        self._session.add(event)

        # Mark Context Summary stale
        await self._session.execute(
            update(ContextSummary)
            .where(ContextSummary.session_id == session_id, ContextSummary.is_stale == False)  # noqa: E712
            .values(is_stale=True)
        )

        await self._session.flush()

        return CancelSessionResult(
            session_id=session_id,
            action=action,
            session_status=TradeSessionStatus.CANCELLED,
        )
