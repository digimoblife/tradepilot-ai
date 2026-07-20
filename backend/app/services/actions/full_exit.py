"""Full Exit Action Service (TP-0506).

Applies a user-confirmed full exit and finalizes the position canonically.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.calculations.exits import (
    ExitFill,
    calculate_gross_closing_pnl,
    calculate_net_closing_pnl,
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

# ---------------------------------------------------------------------------
# Closing reason -> session status mapping (from DOMAIN_VALIDATION_RULES.md)
# ---------------------------------------------------------------------------

CLOSING_REASON_MAP: dict[str, str] = {
    "TAKE_PROFIT": "CLOSED_TAKE_PROFIT",
    "STOP_LOSS": "CLOSED_STOP_LOSS",
    "MANUAL_EXIT": "CLOSED_MANUAL",
}


class FullExitError(Exception):
    code = "FULL_EXIT_ERROR"


class FullExitInvalidStateError(FullExitError):
    code = "FULL_EXIT_INVALID_STATE"


class FullExitInvalidInputError(FullExitError):
    code = "FULL_EXIT_INVALID_INPUT"


class FullExitQuantityMismatchError(FullExitError):
    code = "FULL_EXIT_QUANTITY_MISMATCH"


class FullExitInvalidReasonError(FullExitError):
    code = "FULL_EXIT_INVALID_REASON"


class FullExitInvalidTimelineError(FullExitError):
    code = "FULL_EXIT_INVALID_TIMELINE"


class FullExitNotFoundError(FullExitError):
    code = "FULL_EXIT_NOT_FOUND_OR_NOT_OWNED"


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
class FullExitResult:
    session_id: uuid.UUID
    action: TradeAction
    gross_pnl: object
    net_pnl: object
    weighted_exit_price: object | None


class FullExitActionService:
    """Confirm a full exit and close the position."""

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
        closing_reason: str,
        fees: object | None = None,
        note: str | None = None,
    ) -> FullExitResult:
        # Load with row locks
        ts = await self._session_repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise FullExitNotFoundError(f"Session {session_id} not found for user {owner_id}")

        tstate = await self._state_repo.get_for_user_for_update(session_id, owner_id)
        if tstate is None:
            raise FullExitNotFoundError(f"Trade state not found for session {session_id}")

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
            return await self._build_idempotent_result(session_id, owner_id, existing)

        # Validate state
        if ts.lifecycle_status not in _VALID_STATES:
            raise FullExitInvalidStateError(
                f"Cannot close: session is {ts.lifecycle_status.value}"
            )
        if tstate.position_status not in _VALID_POSITION_STATES:
            raise FullExitInvalidStateError(
                f"Cannot close: position is {tstate.position_status.value}"
            )

        # Validate closing reason
        terminal_status = CLOSING_REASON_MAP.get(closing_reason)
        if terminal_status is None:
            raise FullExitInvalidReasonError(
                f"Invalid closing reason: {closing_reason}. "
                f"Supported: {', '.join(CLOSING_REASON_MAP)}"
            )

        # Validate decimal inputs
        try:
            d_price = to_decimal(exit_price)  # type: ignore[arg-type]
            d_qty = to_decimal(exit_quantity)  # type: ignore[arg-type]
        except InvalidDecimalError as exc:
            raise FullExitInvalidInputError(str(exc)) from exc

        if d_price <= 0:
            raise FullExitInvalidInputError(f"Exit price must be positive, got {d_price}")
        if d_qty <= 0:
            raise FullExitInvalidInputError(f"Exit quantity must be positive, got {d_qty}")

        d_fees = None
        if fees is not None:
            try:
                d_fees = to_decimal(fees)  # type: ignore[arg-type]
            except InvalidDecimalError as exc:
                raise FullExitInvalidInputError(str(exc)) from exc
            if d_fees < 0:
                raise FullExitInvalidInputError(f"Fees must be non-negative, got {d_fees}")

        prev_rem = tstate.remaining_quantity
        if prev_rem is None or prev_rem <= 0:
            raise FullExitInvalidStateError("No remaining quantity to close")

        # Full exit must close exactly the remaining quantity
        if d_qty != prev_rem:
            raise FullExitQuantityMismatchError(
                f"Full exit quantity ({d_qty}) must equal remaining ({prev_rem})"
            )

        entry_price = tstate.entry_price
        if entry_price is None:
            raise FullExitInvalidStateError("Cannot close: entry price is missing")

        # Timeline: exit must not be before entry
        if tstate.entry_at is not None and executed_at < tstate.entry_at:
            raise FullExitInvalidTimelineError(
                f"Exit timestamp ({executed_at}) is before entry ({tstate.entry_at})"
            )

        # Calculate incremental P&L for this final exit
        incremental_pnl = calculate_partial_realized_pnl(d_price, entry_price, d_qty)
        prev_realized = tstate.realized_pnl if tstate.realized_pnl is not None else 0
        new_realized = prev_realized + incremental_pnl

        # Calculate weighted average exit across all exits
        fills: list[ExitFill] = []
        prev_avg_exit = tstate.average_exit_price
        prev_exited_qty = (tstate.original_quantity or 0) - prev_rem
        if prev_avg_exit is not None and prev_exited_qty > 0:
            fills.append(ExitFill(price=prev_avg_exit, quantity=prev_exited_qty))
        fills.append(ExitFill(price=d_price, quantity=d_qty))
        new_avg_exit = calculate_weighted_average_exit(tuple(fills))

        # Gross and net closing result via TP-0304 helpers
        total_qty = tstate.original_quantity or d_qty
        gross_pnl = calculate_gross_closing_pnl(entry_price, total_qty, new_avg_exit or d_price)
        total_fees: object = d_fees if d_fees is not None else Decimal("0")
        net_pnl = calculate_net_closing_pnl(gross_pnl, total_fees)  # type: ignore[arg-type]

        # Set terminal session status
        terminal_enum = TradeSessionStatus(terminal_status)

        # Create action
        action = TradeAction(
            session_id=session_id,
            action_type=ActionType.FULL_EXIT,
            confirmed_at=executed_at,
            price=d_price,
            quantity=d_qty,
            idempotency_key=idempotency_key,
            note=note,
            payload={
                "closing_reason": closing_reason,
                "previous_remaining": str(prev_rem),
                "gross_pnl": str(gross_pnl),
                "net_pnl": str(net_pnl),
                "weighted_exit": str(new_avg_exit) if new_avg_exit else str(d_price),
            },
        )
        self._session.add(action)

        # Update TradeState to CLOSED
        tstate.position_status = PositionStatus.CLOSED
        tstate.remaining_quantity = Decimal("0")
        tstate.realized_pnl = new_realized
        if new_avg_exit is not None:
            tstate.average_exit_price = new_avg_exit
        tstate.active_stop_loss = None
        tstate.active_target = None
        tstate.last_confirmed_action_at = executed_at

        # Update session lifecycle
        ts.lifecycle_status = terminal_enum
        ts.stable_status = terminal_enum

        # Create event
        event = SessionEvent(
            session_id=session_id,
            event_type=SessionEventType.FULL_EXIT,
            occurred_at=executed_at,
            related_action_id=action.id,
            price=d_price,
            quantity=d_qty,
            compact_summary=f"Position closed: {closing_reason}, P&L={gross_pnl}",
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
            reason=ContextRebuildReason.FULL_EXIT,
            source_id=action.id,
        )

        return FullExitResult(
            session_id=session_id,
            action=action,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            weighted_exit_price=new_avg_exit,
        )

    async def _build_idempotent_result(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        action: TradeAction,
    ) -> FullExitResult:
        tstate = await self._state_repo.get_for_user(session_id, owner_id)
        return FullExitResult(
            session_id=session_id,
            action=action,
            gross_pnl=tstate.realized_pnl if tstate else 0,
            net_pnl=tstate.realized_pnl if tstate else 0,
            weighted_exit_price=tstate.average_exit_price if tstate else None,
        )
