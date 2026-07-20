"""Open Position Service (TP-0503).

Atomically confirms a user's actual position entry, creating the canonical
Trade Action, updating Trade State, session lifecycle, session event, and
marking Context Summary stale.
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
from app.models.enums import ActionType, PositionStatus, SessionEventType, TradeSessionStatus
from app.models.session_event import SessionEvent
from app.models.trade_action import TradeAction
from app.models.trade_state import TradeState
from app.repositories.trade_session import TradeSessionRepository
from app.repositories.trade_state import TradeStateRepository
from app.services.context_rebuild import ContextRebuildReason, ContextRebuildService


class OpenPositionError(Exception):
    """Base error for position open operations."""

    code = "POSITION_OPEN_ERROR"


class OpenPositionInvalidStateError(OpenPositionError):
    code = "POSITION_OPEN_INVALID_STATE"


class OpenPositionInvalidInputError(OpenPositionError):
    code = "POSITION_OPEN_INVALID_INPUT"


class OpenPositionNotFoundError(OpenPositionError):
    code = "POSITION_OPEN_NOT_FOUND_OR_NOT_OWNED"


class OpenPositionIdempotencyError(OpenPositionError):
    code = "POSITION_OPEN_IDEMPOTENCY_CONFLICT"


@dataclass(frozen=True, slots=True)
class OpenPositionResult:
    session_id: uuid.UUID
    action: TradeAction
    trade_state: TradeState
    session_status: TradeSessionStatus


class OpenPositionService:
    """Confirm a real position and make confirmed values canonical."""

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
        entry_price: object,
        quantity: object,
        execution_timestamp: datetime,
        stop_loss: object | None = None,
        target: object | None = None,
        note: str | None = None,
    ) -> OpenPositionResult:
        """Confirm a position open.

        Performs all steps atomically in one transaction.
        """
        # 1. Load session and state with row locks
        ts = await self._session_repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise OpenPositionNotFoundError(f"Session {session_id} not found for user {owner_id}")

        tstate = await self._state_repo.get_for_user_for_update(session_id, owner_id)
        if tstate is None:
            raise OpenPositionNotFoundError(f"Trade state not found for session {session_id}")

        # 2. Check idempotency FIRST (before state validation)
        existing_action = await self._session.execute(
            select(TradeAction).where(
                TradeAction.session_id == session_id,
                TradeAction.idempotency_key == idempotency_key,
            )
        )
        existing = existing_action.unique().scalar_one_or_none()
        if existing is not None:
            current_state = await self._state_repo.get_for_user(session_id, owner_id)
            return OpenPositionResult(
                session_id=session_id,
                action=existing,
                trade_state=current_state or tstate,
                session_status=ts.lifecycle_status,
            )

        # 3. Validate current state
        if ts.lifecycle_status != TradeSessionStatus.WATCHING:
            raise OpenPositionInvalidStateError(
                f"Cannot open position: session is {ts.lifecycle_status.value}, expected WATCHING"
            )

        # 4. Validate inputs
        try:
            d_entry = to_decimal(entry_price)
            d_qty = to_decimal(quantity)
        except InvalidDecimalError as exc:
            raise OpenPositionInvalidInputError(str(exc)) from exc

        if d_entry <= 0:
            raise OpenPositionInvalidInputError(f"Entry price must be positive, got {d_entry}")
        if d_qty <= 0:
            raise OpenPositionInvalidInputError(f"Quantity must be positive, got {d_qty}")

        d_stop: object | None = None
        if stop_loss is not None:
            try:
                d_stop = to_decimal(stop_loss)
            except InvalidDecimalError as exc:
                raise OpenPositionInvalidInputError(str(exc)) from exc

        d_target: object | None = None
        if target is not None:
            try:
                d_target = to_decimal(target)
            except InvalidDecimalError as exc:
                raise OpenPositionInvalidInputError(str(exc)) from exc

        # 5. Create TradeAction
        action = TradeAction(
            session_id=session_id,
            action_type=ActionType.POSITION_OPENED,
            confirmed_at=execution_timestamp,
            price=d_entry,
            quantity=d_qty,
            idempotency_key=idempotency_key,
            note=note,
            payload={
                "confirmed_stop": str(d_stop) if d_stop else None,
                "confirmed_target": str(d_target) if d_target else None,
            },
        )
        self._session.add(action)

        # 6. Update TradeState
        tstate.position_status = PositionStatus.OPEN
        tstate.entry_price = d_entry
        tstate.entry_at = execution_timestamp
        tstate.original_quantity = d_qty
        tstate.remaining_quantity = d_qty
        tstate.active_stop_loss = d_stop
        tstate.active_target = d_target
        tstate.last_confirmed_action_at = execution_timestamp

        # 7. Update session lifecycle
        ts.lifecycle_status = TradeSessionStatus.OPEN_POSITION
        ts.stable_status = TradeSessionStatus.OPEN_POSITION

        # 8. Create SessionEvent
        event = SessionEvent(
            session_id=session_id,
            event_type=SessionEventType.POSITION_OPENED,
            occurred_at=execution_timestamp,
            related_action_id=action.id,
            price=d_entry,
            quantity=d_qty,
            compact_summary=f"Position opened at {d_entry} x {d_qty}",
        )
        self._session.add(event)

        # 9. Rebuild Context Summary
        await self._session.execute(
            update(ContextSummary)
            .where(
                ContextSummary.session_id == session_id,
                ContextSummary.is_stale == False,  # noqa: E712
            )
            .values(is_stale=True)
        )
        await self._session.flush()

        rebuild = ContextRebuildService(self._session)
        await rebuild.rebuild_after_material_event(
            session_id=session_id,
            owner_id=owner_id,
            reason=ContextRebuildReason.POSITION_OPENED,
            source_id=action.id,
        )

        return OpenPositionResult(
            session_id=session_id,
            action=action,
            trade_state=tstate,
            session_status=ts.lifecycle_status,
        )
