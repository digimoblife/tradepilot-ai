from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.session_decision import (
    SessionDecisionV2,
    SessionDecisionV2Decision,
)
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


class BuyDecisionError(Exception):
    code = "BUY_DECISION_FAILED"
    status_code = 422


class BuyDecisionSessionNotFoundError(BuyDecisionError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class BuyDecisionNotAllowedError(BuyDecisionError):
    code = "BUY_NOT_ALLOWED"
    status_code = 409


class BuyDecisionAlreadyExistsError(BuyDecisionError):
    code = "BUY_ALREADY_EXISTS"
    status_code = 409


class BuyDecisionPositionExistsError(BuyDecisionError):
    code = "BUY_POSITION_EXISTS"
    status_code = 409


class BuyDecisionPersistenceError(BuyDecisionError):
    code = "BUY_DECISION_PERSISTENCE_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class BuyDecisionResult:
    decision_id: uuid.UUID
    session_id: uuid.UUID
    decision_type: SessionDecisionV2Decision
    decision_at: datetime
    position_id: uuid.UUID
    position_status: PositionV2Status
    entry_price: Decimal
    entry_timestamp: datetime
    quantity: Decimal
    stop_loss: Decimal
    target_price: Decimal
    note: str | None
    session_status: TradeSessionV2Status


class BuyDecisionService:
    """Persist one confirmed BUY and one open position for one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        entry_price: Decimal,
        entry_timestamp: datetime,
        quantity: Decimal,
        stop_loss: Decimal,
        target_price: Decimal,
        note: str | None,
    ) -> BuyDecisionResult:
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
            raise BuyDecisionSessionNotFoundError("Rebuild session was not found")
        if trade_session.status not in {
            TradeSessionV2Status.DRAFT,
            TradeSessionV2Status.ANALYZED,
            TradeSessionV2Status.WAITING,
        }:
            raise BuyDecisionNotAllowedError(
                "BUY is not allowed for the current session status"
            )
        if await self._session.scalar(
            select(PositionV2.id).where(PositionV2.session_id == session_id).limit(1)
        ) is not None:
            raise BuyDecisionPositionExistsError(
                "BUY is not allowed for a session with an existing position"
            )
        if await self._session.scalar(
            select(SessionDecisionV2.id)
            .where(
                SessionDecisionV2.session_id == session_id,
                SessionDecisionV2.decision == SessionDecisionV2Decision.BUY,
            )
            .limit(1)
        ) is not None:
            raise BuyDecisionAlreadyExistsError(
                "A BUY decision already exists for this session"
            )

        decision = SessionDecisionV2(
            session_id=session_id,
            decision=SessionDecisionV2Decision.BUY,
            note=note,
        )
        position = PositionV2(
            session_id=session_id,
            entry_price=entry_price,
            entry_at=entry_timestamp,
            quantity=quantity,
            stop_loss=stop_loss,
            target_price=target_price,
            status=PositionV2Status.OPEN,
        )
        self._session.add_all([decision, position])
        trade_session.status = TradeSessionV2Status.OPEN_POSITION
        trade_session.closed_at = None
        try:
            await self._session.flush()
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise BuyDecisionPersistenceError(
                "BUY decision could not be persisted"
            ) from exc
        return BuyDecisionResult(
            decision_id=decision.id,
            session_id=trade_session.id,
            decision_type=decision.decision,
            decision_at=decision.created_at,
            position_id=position.id,
            position_status=position.status,
            entry_price=position.entry_price,
            entry_timestamp=position.entry_at,
            quantity=position.quantity,
            stop_loss=position.stop_loss,
            target_price=position.target_price,
            note=decision.note,
            session_status=trade_session.status,
        )


def _session_lock_key(session_id: uuid.UUID) -> int:
    return int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
