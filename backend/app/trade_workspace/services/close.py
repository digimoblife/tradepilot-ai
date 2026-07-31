from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


class CloseError(Exception):
    code = "CLOSE_FAILED"
    status_code = 422


class CloseSessionNotFoundError(CloseError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class CloseNotAllowedError(CloseError):
    code = "CLOSE_NOT_ALLOWED"
    status_code = 409


class CloseNoOpenPositionError(CloseError):
    code = "CLOSE_NO_OPEN_POSITION"
    status_code = 409


class CloseMultiplePositionsError(CloseError):
    code = "CLOSE_MULTIPLE_POSITIONS"
    status_code = 409


class ClosePositionAlreadyClosedError(CloseError):
    code = "CLOSE_POSITION_ALREADY_CLOSED"
    status_code = 409


class CloseAlreadyExistsError(CloseError):
    code = "CLOSE_ALREADY_EXISTS"
    status_code = 409


class CloseValidationError(CloseError):
    code = "CLOSE_INVALID_INPUT"
    status_code = 422


class ClosePersistenceError(CloseError):
    code = "CLOSE_PERSISTENCE_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class CloseResult:
    closure_id: uuid.UUID
    session_id: uuid.UUID
    position_id: uuid.UUID
    close_price: Decimal
    close_timestamp: datetime
    close_reason: str
    note: str | None
    realized_profit_loss: Decimal
    position_status: PositionV2Status
    session_status: TradeSessionV2Status
    closed_at: datetime
    created_at: datetime


class CloseService:
    """Execute CLOSE action for a confirmed open position in one trade session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        close_price: Decimal,
        close_timestamp: datetime,
        close_reason: str,
        note: str | None = None,
    ) -> CloseResult:
        self._validate(close_price, close_timestamp, close_reason)

        await self._session.execute(
            select(func.pg_advisory_xact_lock(_session_lock_key(session_id)))
        )

        trade_session = await self._session.scalar(
            select(TradeSessionV2)
            .where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
            .with_for_update()
        )
        if trade_session is None:
            raise CloseSessionNotFoundError("Rebuild session was not found")

        if trade_session.status is not TradeSessionV2Status.OPEN_POSITION:
            raise CloseNotAllowedError(
                "CLOSE is only allowed for OPEN_POSITION sessions"
            )

        positions = list(
            (
                await self._session.scalars(
                    select(PositionV2)
                    .where(PositionV2.session_id == session_id)
                    .with_for_update()
                )
            ).all()
        )

        if len(positions) == 0:
            raise CloseNoOpenPositionError("No position found for this session")
        if len(positions) > 1:
            raise CloseMultiplePositionsError("Multiple positions found for this session")

        position = positions[0]
        if position.status is not PositionV2Status.OPEN:
            raise ClosePositionAlreadyClosedError("Position is already closed")

        existing_closure = await self._session.scalar(
            select(TradeClosureV2.id)
            .where(TradeClosureV2.position_id == position.id)
            .limit(1)
        )
        if existing_closure is not None:
            raise CloseAlreadyExistsError("A closure record already exists for this position")

        realized_profit_loss = (close_price - position.entry_price) * position.quantity

        closure = TradeClosureV2(
            session_id=session_id,
            position_id=position.id,
            close_price=close_price,
            close_at=close_timestamp,
            close_reason=close_reason.strip(),
            note=note,
            realized_profit_loss=realized_profit_loss,
        )
        self._session.add(closure)

        position.status = PositionV2Status.CLOSED
        position.closed_at = close_timestamp

        trade_session.status = TradeSessionV2Status.CLOSED
        trade_session.closed_at = close_timestamp

        try:
            await self._session.flush()
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise ClosePersistenceError("CLOSE record could not be persisted") from exc

        return CloseResult(
            closure_id=closure.id,
            session_id=session_id,
            position_id=position.id,
            close_price=closure.close_price,
            close_timestamp=closure.close_at,
            close_reason=closure.close_reason,
            note=closure.note,
            realized_profit_loss=closure.realized_profit_loss,
            position_status=position.status,
            session_status=trade_session.status,
            closed_at=trade_session.closed_at,
            created_at=closure.created_at,
        )

    def _validate(
        self,
        close_price: Decimal,
        close_timestamp: datetime,
        close_reason: str,
    ) -> None:
        if not close_price.is_finite() or close_price <= 0:
            raise CloseValidationError("Close price must be a positive number")
        decimal_places = max(0, -close_price.as_tuple().exponent)
        if decimal_places > 6 or close_price.adjusted() > 13:
            raise CloseValidationError("Close price exceeds precision limits")
        if close_timestamp.tzinfo is None or close_timestamp.utcoffset() is None:
            raise CloseValidationError("Close timestamp must be timezone-aware")
        if not close_reason or not close_reason.strip():
            raise CloseValidationError("Close reason must not be blank")
        if len(close_reason.strip()) > 64:
            raise CloseValidationError("Close reason exceeds max length of 64 characters")


def _session_lock_key(session_id: uuid.UUID) -> int:
    return int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
