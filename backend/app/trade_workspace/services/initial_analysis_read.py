from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


class InitialAnalysisReadError(Exception):
    """Base error for the rebuild Initial Analysis read contract."""


class InitialAnalysisSessionNotFoundError(InitialAnalysisReadError):
    pass


class InitialAnalysisRequestNotFoundError(InitialAnalysisReadError):
    pass


@dataclass(frozen=True, slots=True)
class InitialAnalysisReadResult:
    analysis_request_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    request_status: AnalysisRequestV2Status
    session_status: TradeSessionV2Status
    processed_response: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class InitialAnalysisReadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> InitialAnalysisReadResult:
        trade_session = await self._session.scalar(
            select(TradeSessionV2).where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
        )
        if trade_session is None:
            raise InitialAnalysisSessionNotFoundError("Rebuild session was not found")

        request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.INITIAL_ANALYSIS,
            )
            .order_by(desc(AnalysisRequestV2.created_at), desc(AnalysisRequestV2.id))
            .limit(1)
        )
        if request is None:
            raise InitialAnalysisRequestNotFoundError(
                "Initial Analysis request was not found"
            )

        is_completed = request.status is AnalysisRequestV2Status.COMPLETED
        is_failed = request.status is AnalysisRequestV2Status.FAILED
        return InitialAnalysisReadResult(
            analysis_request_id=request.id,
            session_id=trade_session.id,
            analysis_type=request.analysis_type,
            request_status=request.status,
            session_status=trade_session.status,
            processed_response=request.processed_response if is_completed else None,
            error_code=request.error_code if is_failed else None,
            error_message=request.error_message if is_failed else None,
            created_at=request.created_at,
            started_at=request.started_at,
            completed_at=request.completed_at,
        )
