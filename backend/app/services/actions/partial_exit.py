"""Partial Exit Action Service (TP-0505).

Applies a user-confirmed partial exit to an active position.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.calculations.exits import (
    ExitFill,
    calculate_partial_realized_pnl,
    calculate_weighted_average_exit,
)
from app.models.context_summary import ContextSummary
from app.models.enums import ActionType, PositionStatus, SessionEventType, TradeSessionStatus
from app.models.session_event import SessionEvent
from app.models.trade_action import TradeAction
from app.repositories.trade_session import TradeSessionRepository
from app.repositories.trade_state import TradeStateRepository
from app.services.context_rebuild import ContextRebuildReason, ContextRebuildService


class PartialExitError(Exception):
    code = "PARTIAL_EXIT_ERROR"


class PartialExitInvalidStateError(PartialExitError):
    code = "PARTIAL_EXIT_INVALID_STATE"


class PartialExitInvalidInputError(PartialExitError):
    code = "PARTIAL_EXIT_INVALID_INPUT"


class PartialExitQuantityInvalidError(PartialExitError):
    code = "PARTIAL_EXIT_QUANTITY_INVALID"


class PartialExitNotFoundError(PartialExitError):
    code = "PARTIAL_EXIT_NOT_FOUND_OR_NOT_OWNED"


_VALID_STATES = frozenset(
    {
        TradeSessionStatus.OPEN_POSITION,
        TradeSessionStatus.PARTIALLY_CLOSED,
    }
)

_VALID_POSITION_STATES = frozenset(
    {
        PositionStatus.OPEN,
        PositionStatus.PARTIALLY_CLOSED,
    }
)


@dataclass(frozen=True, slots=True)
class PartialExitResult:
    session_id: uuid.UUID
    action: TradeAction
    remaining_quantity: object
    realized_pnl: object
    average_exit_price: object | None


class PartialExitActionService:
    """Confirm a partial exit for an active position."""

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
        exit_price: object,
        exit_quantity: object,
        executed_at: datetime,
        reason: str | None = None,
        note: str | None = None,
    ) -> PartialExitResult:
        # Load with row locks
        ts = await self._session_repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise PartialExitNotFoundError(f"Session {session_id} not found for user {owner_id}")

        tstate = await self._state_repo.get_for_user_for_update(session_id, owner_id)
        if tstate is None:
            raise PartialExitNotFoundError(f"Trade state not found for session {session_id}")

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
            return PartialExitResult(
                session_id=session_id,
                action=existing,
                remaining_quantity=tstate.remaining_quantity,
                realized_pnl=tstate.realized_pnl,
                average_exit_price=tstate.average_exit_price,
            )

        # Validate state
        if ts.lifecycle_status not in _VALID_STATES:
            raise PartialExitInvalidStateError(
                f"Cannot exit: session is {ts.lifecycle_status.value}"
            )
        if tstate.position_status not in _VALID_POSITION_STATES:
            raise PartialExitInvalidStateError(
                f"Cannot exit: position is {tstate.position_status.value}"
            )

        # Validate inputs
        try:
            d_price = to_decimal(exit_price)  # type: ignore[arg-type]
            d_qty = to_decimal(exit_quantity)  # type: ignore[arg-type]
        except InvalidDecimalError as exc:
            raise PartialExitInvalidInputError(str(exc)) from exc

        if d_price <= 0:
            raise PartialExitInvalidInputError(f"Exit price must be positive, got {d_price}")
        if d_qty <= 0:
            raise PartialExitInvalidInputError(f"Exit quantity must be positive, got {d_qty}")

        prev_rem = tstate.remaining_quantity
        if prev_rem is None or prev_rem <= 0:
            raise PartialExitInvalidStateError("No remaining quantity to exit")

        # Partial must sell LESS than remaining
        if d_qty >= prev_rem:
            raise PartialExitQuantityInvalidError(
                f"Partial exit quantity ({d_qty}) must be less than remaining ({prev_rem})"
            )

        new_rem = prev_rem - d_qty
        if new_rem <= 0:
            raise PartialExitQuantityInvalidError(
                f"Resulting remaining ({new_rem}) must be positive"
            )

        # Ensure entry price exists for calculations
        entry_price = tstate.entry_price
        if entry_price is None:
            raise PartialExitInvalidStateError("Cannot exit: entry price is missing")

        # Calculate realized P&L for this exit
        incremental_pnl = calculate_partial_realized_pnl(d_price, entry_price, d_qty)
        prev_realized = tstate.realized_pnl if tstate.realized_pnl is not None else 0
        new_realized = prev_realized + incremental_pnl

        # Calculate weighted average exit
        # Collect previous exit fills from existing average_exit_price and remaining
        prev_avg_exit = tstate.average_exit_price
        fills: list[ExitFill] = []
        # We don't store individual fills in the TradeState, so reconstruct from
        # the previous average exit price.  If a previous average exists, we treat
        # it as one fill with the total previously exited quantity.
        prev_exited_qty = tstate.original_quantity - prev_rem if tstate.original_quantity else 0
        if prev_avg_exit is not None and prev_exited_qty > 0:
            fills.append(ExitFill(price=prev_avg_exit, quantity=prev_exited_qty))  # type: ignore[arg-type]
        fills.append(ExitFill(price=d_price, quantity=d_qty))
        new_avg_exit = calculate_weighted_average_exit(tuple(fills))

        # Create action
        action = TradeAction(
            session_id=session_id,
            action_type=ActionType.PARTIAL_EXIT,
            confirmed_at=executed_at,
            price=d_price,
            quantity=d_qty,
            idempotency_key=idempotency_key,
            note=note or reason,
            payload={
                "reason": reason,
                "previous_remaining": str(prev_rem),
                "new_remaining": str(new_rem),
                "incremental_pnl": str(incremental_pnl),
                "cumulative_pnl": str(new_realized),
            },
        )
        self._session.add(action)

        # Update TradeState
        tstate.position_status = PositionStatus.PARTIALLY_CLOSED
        tstate.remaining_quantity = new_rem
        tstate.realized_pnl = new_realized
        if new_avg_exit is not None:
            tstate.average_exit_price = new_avg_exit
        tstate.last_confirmed_action_at = executed_at

        # Update session lifecycle
        ts.lifecycle_status = TradeSessionStatus.PARTIALLY_CLOSED
        ts.stable_status = TradeSessionStatus.PARTIALLY_CLOSED

        # Create event
        event = SessionEvent(
            session_id=session_id,
            event_type=SessionEventType.PARTIAL_EXIT,
            occurred_at=executed_at,
            related_action_id=action.id,
            price=d_price,
            quantity=d_qty,
            compact_summary=f"Partial exit {d_qty} @ {d_price}",
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
            reason=ContextRebuildReason.PARTIAL_EXIT,
            source_id=action.id,
        )

        return PartialExitResult(
            session_id=session_id,
            action=action,
            remaining_quantity=new_rem,
            realized_pnl=new_realized,
            average_exit_price=new_avg_exit,
        )
