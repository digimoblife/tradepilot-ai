from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.position import PositionV2
from app.trade_workspace.models.session_decision import (
    SessionDecisionV2,
    SessionDecisionV2Decision,
)
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


class WaitDecisionError(Exception):
    code = "WAIT_DECISION_FAILED"
    status_code = 422


class WaitDecisionSessionNotFoundError(WaitDecisionError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class WaitDecisionNotAllowedError(WaitDecisionError):
    code = "WAIT_NOT_ALLOWED"
    status_code = 409


class WaitDecisionPositionExistsError(WaitDecisionError):
    code = "WAIT_POSITION_EXISTS"
    status_code = 409


class WaitDecisionPersistenceError(WaitDecisionError):
    code = "WAIT_DECISION_PERSISTENCE_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class WaitDecisionResult:
    decision_id: uuid.UUID
    session_id: uuid.UUID
    decision_type: SessionDecisionV2Decision
    decision_at: datetime
    session_status: TradeSessionV2Status


class WaitDecisionService:
    """Persist one user-confirmed WAIT decision atomically for one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: uuid.UUID, session_id: uuid.UUID
    ) -> WaitDecisionResult:
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
            raise WaitDecisionSessionNotFoundError("Rebuild session was not found")
        if trade_session.status not in {
            TradeSessionV2Status.DRAFT,
            TradeSessionV2Status.ANALYZED,
            TradeSessionV2Status.WAITING,
        }:
            raise WaitDecisionNotAllowedError(
                "WAIT is not allowed for the current session status"
            )
        if await self._session.scalar(
            select(PositionV2.id).where(PositionV2.session_id == session_id).limit(1)
        ) is not None:
            raise WaitDecisionPositionExistsError(
                "WAIT is not allowed for a session with an existing position"
            )

        decision = SessionDecisionV2(
            session_id=session_id,
            decision=SessionDecisionV2Decision.WAIT,
        )
        self._session.add(decision)
        trade_session.status = TradeSessionV2Status.WAITING
        try:
            await self._session.flush()
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise WaitDecisionPersistenceError(
                "WAIT decision could not be persisted"
            ) from exc
        return WaitDecisionResult(
            decision_id=decision.id,
            session_id=trade_session.id,
            decision_type=decision.decision,
            decision_at=decision.created_at,
            session_status=trade_session.status,
        )


def _session_lock_key(session_id: uuid.UUID) -> int:
    return int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
