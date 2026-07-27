"""Repository for EvaluationRecord persistence (P7)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation_record import EvaluationRecord
from app.models.trade_session import TradeSession, normalize_ticker


class EvaluationRecordRepository:
    """Async repository for EvaluationRecord entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, record: EvaluationRecord) -> EvaluationRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_id(self, record_id: uuid.UUID, owner_id: uuid.UUID) -> EvaluationRecord | None:
        query = select(EvaluationRecord).where(
            and_(
                EvaluationRecord.id == record_id,
                EvaluationRecord.owner_id == owner_id,
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_session_and_analysis(
        self,
        session_id: uuid.UUID,
        source_analysis_id: uuid.UUID,
    ) -> EvaluationRecord | None:
        query = select(EvaluationRecord).where(
            and_(
                EvaluationRecord.session_id == session_id,
                EvaluationRecord.source_analysis_id == source_analysis_id,
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_for_session(self, session_id: uuid.UUID) -> EvaluationRecord | None:
        query = (
            select(EvaluationRecord)
            .where(EvaluationRecord.session_id == session_id)
            .order_by(EvaluationRecord.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: uuid.UUID,
        *,
        ticker: str | None = None,
        analysis_type: str | None = None,
        completeness_status: str | None = None,
        session_status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[EvaluationRecord], int]:
        filters = [EvaluationRecord.owner_id == owner_id]

        if ticker:
            filters.append(func.upper(func.trim(EvaluationRecord.ticker)) == normalize_ticker(ticker))
        if analysis_type:
            filters.append(EvaluationRecord.analysis_type == analysis_type)
        if completeness_status:
            filters.append(EvaluationRecord.completeness_status == completeness_status)

        query = select(EvaluationRecord).where(and_(*filters))

        if session_status:
            query = query.join(TradeSession, EvaluationRecord.session_id == TradeSession.id).where(
                TradeSession.lifecycle_status == session_status
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await self._session.execute(count_query)
        total = total_res.scalar_one() or 0

        # Paginate
        query = query.order_by(EvaluationRecord.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        records = list(result.scalars().all())

        return records, total
