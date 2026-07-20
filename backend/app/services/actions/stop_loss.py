"""Stop Loss Confirmation Service (TP-0504).

User-confirmed active stop loss changes for an existing long position.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.models.context_summary import ContextSummary
from app.models.enums import ActionType, SessionEventType, TradeSessionStatus
from app.models.session_event import SessionEvent
from app.models.trade_action import TradeAction
from app.repositories.trade_session import TradeSessionRepository
from app.repositories.trade_state import TradeStateRepository
from app.services.context_rebuild import ContextRebuildReason, ContextRebuildService


class StopLossError(Exception):
    code = "STOP_LOSS_ERROR"


class StopLossInvalidStateError(StopLossError):
    code = "STOP_LOSS_INVALID_STATE"


class StopLossInvalidInputError(StopLossError):
    code = "STOP_LOSS_INVALID_INPUT"


class StopLossInvalidRelationshipError(StopLossError):
    code = "STOP_LOSS_INVALID_RELATIONSHIP"


class StopLossNotFoundError(StopLossError):
    code = "STOP_LOSS_NOT_FOUND_OR_NOT_OWNED"


_VALID_STATES = frozenset(
    {
        TradeSessionStatus.OPEN_POSITION,
        TradeSessionStatus.PARTIALLY_CLOSED,
    }
)


@dataclass(frozen=True, slots=True)
class StopLossActionResult:
    session_id: uuid.UUID
    action: TradeAction
    active_stop_loss: object
    action_type: ActionType


class StopLossActionService:
    """Confirm or change the active stop loss for a long position."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_repo = TradeSessionRepository(session)
        self._state_repo = TradeStateRepository(session)

    async def confirm(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        idempotency_key: str,
        stop_loss: object,
        confirmed_at: datetime,
        note: str | None = None,
    ) -> StopLossActionResult:
        ts = await self._session_repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise StopLossNotFoundError(f"Session {session_id} not found for user {owner_id}")

        tstate = await self._state_repo.get_for_user_for_update(session_id, owner_id)
        if tstate is None:
            raise StopLossNotFoundError(f"Trade state not found for session {session_id}")

        # Idempotency first
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
            return StopLossActionResult(
                session_id=session_id,
                action=existing,
                active_stop_loss=tstate.active_stop_loss,
                action_type=existing.action_type,
            )

        # Validate state
        if ts.lifecycle_status not in _VALID_STATES:
            raise StopLossInvalidStateError(
                f"Cannot change stop loss: session is {ts.lifecycle_status.value}"
            )

        # Validate input
        try:
            d_stop = to_decimal(stop_loss)
        except InvalidDecimalError as exc:
            raise StopLossInvalidInputError(str(exc)) from exc
        if d_stop <= 0:
            raise StopLossInvalidInputError(f"Stop loss must be positive, got {d_stop}")

        # Validate relationship: stop < entry price
        if tstate.entry_price is None or d_stop >= tstate.entry_price:
            raise StopLossInvalidRelationshipError(
                f"Stop loss ({d_stop}) must be below entry price ({tstate.entry_price})"
            )

        # Determine action type
        has_existing = tstate.active_stop_loss is not None
        action_type = (
            ActionType.STOP_LOSS_CHANGED if has_existing else ActionType.STOP_LOSS_CONFIRMED
        )

        # Create action
        action = TradeAction(
            session_id=session_id,
            action_type=action_type,
            confirmed_at=confirmed_at,
            price=d_stop,
            idempotency_key=idempotency_key,
            note=note,
            payload={
                "previous_stop": str(tstate.active_stop_loss) if tstate.active_stop_loss else None
            },
        )
        self._session.add(action)

        # Update TradeState
        tstate.active_stop_loss = d_stop
        tstate.last_confirmed_action_at = confirmed_at

        # Create event
        event = SessionEvent(
            session_id=session_id,
            event_type=SessionEventType.STOP_LOSS_CHANGED,
            occurred_at=confirmed_at,
            related_action_id=action.id,
            price=d_stop,
            compact_summary=f"Stop loss set to {d_stop}",
        )
        self._session.add(event)

        # Mark Context Summary stale
        await self._session.execute(
            update(ContextSummary)
            .where(ContextSummary.session_id == session_id, ContextSummary.is_stale == False)  # noqa: E712
            .values(is_stale=True)
        )
        await self._session.flush()

        rebuild = ContextRebuildService(self._session)
        await rebuild.rebuild_after_material_event(
            session_id=session_id,
            owner_id=owner_id,
            reason=ContextRebuildReason.STOP_LOSS_CHANGED,
            source_id=action.id,
        )

        return StopLossActionResult(
            session_id=session_id,
            action=action,
            active_stop_loss=d_stop,
            action_type=action_type,
        )
