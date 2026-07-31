from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


class PositionUpdateReadError(Exception):
    """Base error for the rebuild Position Update read contract."""


class PositionUpdateReadNotFoundError(PositionUpdateReadError):
    pass


@dataclass(frozen=True, slots=True)
class PositionDetailReadResult:
    id: uuid.UUID
    session_id: uuid.UUID
    status: PositionV2Status
    entry_price: Decimal
    entry_at: datetime
    quantity: Decimal
    stop_loss: Decimal
    target_price: Decimal
    note: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PositionUpdateItemReadResult:
    analysis_request_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    request_status: AnalysisRequestV2Status
    current_price: Decimal | None
    observation_period: AnalysisRequestV2ObservationPeriod | None
    observation_at: datetime | None
    processed_response: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    evidence_id: uuid.UUID | None = None
    original_filename: str | None = None


@dataclass(frozen=True, slots=True)
class PositionUpdateReadResult:
    position: PositionDetailReadResult | None
    updates: list[PositionUpdateItemReadResult]


class PositionUpdateReadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> PositionUpdateReadResult:
        trade_session = await self._session.scalar(
            select(TradeSessionV2).where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
        )
        if trade_session is None:
            raise PositionUpdateReadNotFoundError("Rebuild session was not found")

        position_record = await self._session.scalar(
            select(PositionV2).where(
                PositionV2.session_id == session_id,
            )
        )
        position_res = (
            PositionDetailReadResult(
                id=position_record.id,
                session_id=position_record.session_id,
                status=position_record.status,
                entry_price=position_record.entry_price,
                entry_at=position_record.entry_at,
                quantity=position_record.quantity,
                stop_loss=position_record.stop_loss,
                target_price=position_record.target_price,
                note=position_record.note,
                created_at=position_record.created_at,
            )
            if position_record is not None
            else None
        )

        requests = (
            await self._session.scalars(
                select(AnalysisRequestV2)
                .where(
                    AnalysisRequestV2.session_id == session_id,
                    AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.POSITION_UPDATE,
                )
                .order_by(
                    AnalysisRequestV2.created_at.asc(),
                    AnalysisRequestV2.id.asc(),
                )
            )
        ).all()

        evidence_by_request_id: dict[uuid.UUID, EvidenceUploadV2] = {}
        if requests:
            request_ids = [r.id for r in requests]
            ev_records = (
                await self._session.scalars(
                    select(EvidenceUploadV2).where(
                        EvidenceUploadV2.analysis_request_id.in_(request_ids)
                    )
                )
            ).all()
            for ev in ev_records:
                if ev.analysis_request_id:
                    evidence_by_request_id[ev.analysis_request_id] = ev

        items: list[PositionUpdateItemReadResult] = []
        for r in requests:
            ev_rec = evidence_by_request_id.get(r.id)
            is_completed = r.status is AnalysisRequestV2Status.COMPLETED
            is_failed = r.status is AnalysisRequestV2Status.FAILED
            items.append(
                PositionUpdateItemReadResult(
                    analysis_request_id=r.id,
                    session_id=r.session_id,
                    analysis_type=r.analysis_type,
                    request_status=r.status,
                    current_price=r.current_price,
                    observation_period=r.observation_period,
                    observation_at=r.observation_at,
                    processed_response=r.processed_response if is_completed else None,
                    error_code=r.error_code[:64] if is_failed and r.error_code else None,
                    error_message=(
                        r.error_message[:500] if is_failed and r.error_message else None
                    ),
                    created_at=r.created_at,
                    started_at=r.started_at,
                    completed_at=r.completed_at,
                    evidence_id=ev_rec.id if ev_rec else None,
                    original_filename=ev_rec.original_filename if ev_rec else None,
                )
            )

        return PositionUpdateReadResult(
            position=position_res,
            updates=items,
        )
