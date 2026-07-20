"""Target Confirmation Service (TP-0504).

User-confirmed active target changes for an existing long position.
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


class TargetError(Exception):
    code = "TARGET_ERROR"


class TargetInvalidStateError(TargetError):
    code = "TARGET_INVALID_STATE"


class TargetInvalidInputError(TargetError):
    code = "TARGET_INVALID_INPUT"


class TargetInvalidRelationshipError(TargetError):
    code = "TARGET_INVALID_RELATIONSHIP"


class TargetNotFoundError(TargetError):
    code = "TARGET_NOT_FOUND_OR_NOT_OWNED"


_VALID_STATES = frozenset(
    {
        TradeSessionStatus.OPEN_POSITION,
        TradeSessionStatus.PARTIALLY_CLOSED,
    }
)


@dataclass(frozen=True, slots=True)
class TargetActionResult:
    session_id: uuid.UUID
    action: TradeAction
    active_target: object
    action_type: ActionType


class TargetActionService:
    """Confirm or change the active target for a long position."""

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
        target: object,
        confirmed_at: datetime,
        note: str | None = None,
    ) -> TargetActionResult:
        ts = await self._session_repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise TargetNotFoundError(f"Session {session_id} not found for user {owner_id}")

        tstate = await self._state_repo.get_for_user_for_update(session_id, owner_id)
        if tstate is None:
            raise TargetNotFoundError(f"Trade state not found for session {session_id}")

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
            return TargetActionResult(
                session_id=session_id,
                action=existing,
                active_target=tstate.active_target,
                action_type=existing.action_type,
            )

        # Validate state
        if ts.lifecycle_status not in _VALID_STATES:
            raise TargetInvalidStateError(
                f"Cannot change target: session is {ts.lifecycle_status.value}"
            )

        # Validate input
        try:
            d_target = to_decimal(target)
        except InvalidDecimalError as exc:
            raise TargetInvalidInputError(str(exc)) from exc
        if d_target <= 0:
            raise TargetInvalidInputError(f"Target must be positive, got {d_target}")

        # Validate relationship: target > entry price
        if tstate.entry_price is None or d_target <= tstate.entry_price:
            raise TargetInvalidRelationshipError(
                f"Target ({d_target}) must be above entry price ({tstate.entry_price})"
            )

        # Determine action type
        has_existing = tstate.active_target is not None
        action_type = ActionType.TARGET_CHANGED if has_existing else ActionType.TARGET_CONFIRMED

        # Create action
        action = TradeAction(
            session_id=session_id,
            action_type=action_type,
            confirmed_at=confirmed_at,
            price=d_target,
            idempotency_key=idempotency_key,
            note=note,
            payload={
                "previous_target": str(tstate.active_target) if tstate.active_target else None
            },
        )
        self._session.add(action)

        # Update TradeState
        tstate.active_target = d_target
        tstate.last_confirmed_action_at = confirmed_at

        # Create event
        event = SessionEvent(
            session_id=session_id,
            event_type=SessionEventType.TARGET_CHANGED,
            occurred_at=confirmed_at,
            related_action_id=action.id,
            price=d_target,
            compact_summary=f"Target set to {d_target}",
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
            reason=ContextRebuildReason.TARGET_CHANGED,
            source_id=action.id,
        )

        return TargetActionResult(
            session_id=session_id,
            action=action,
            active_target=d_target,
            action_type=action_type,
        )
