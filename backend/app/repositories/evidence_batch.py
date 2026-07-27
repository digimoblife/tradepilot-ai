from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AnalysisType, EvidenceBatchStatus
from app.models.evidence_batch import EvidenceBatch
from app.models.trade_session import TradeSession


class EvidenceBatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: EvidenceBatch) -> EvidenceBatch:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_for_user(
        self,
        batch_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> EvidenceBatch | None:
        query = (
            select(EvidenceBatch)
            .join(TradeSession, EvidenceBatch.session_id == TradeSession.id)
            .where(EvidenceBatch.id == batch_id, TradeSession.owner_id == user_id)
        )
        if for_update:
            query = query.with_for_update()
        result = await self._session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_latest_for_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        analysis_type: AnalysisType,
        *,
        for_update: bool = False,
    ) -> EvidenceBatch | None:
        query = (
            select(EvidenceBatch)
            .join(TradeSession, EvidenceBatch.session_id == TradeSession.id)
            .where(
                EvidenceBatch.session_id == session_id,
                TradeSession.owner_id == user_id,
                EvidenceBatch.analysis_type == analysis_type,
            )
            .order_by(EvidenceBatch.sequence_number.desc())
            .limit(1)
        )
        if for_update:
            query = query.with_for_update()
        result = await self._session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_latest_by_status(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        analysis_type: AnalysisType,
        status: EvidenceBatchStatus,
        *,
        for_update: bool = False,
    ) -> EvidenceBatch | None:
        query = (
            select(EvidenceBatch)
            .join(TradeSession, EvidenceBatch.session_id == TradeSession.id)
            .where(
                EvidenceBatch.session_id == session_id,
                TradeSession.owner_id == user_id,
                EvidenceBatch.analysis_type == analysis_type,
                EvidenceBatch.status == status,
            )
            .order_by(EvidenceBatch.sequence_number.desc())
            .limit(1)
        )
        if for_update:
            query = query.with_for_update()
        result = await self._session.execute(query)
        return result.unique().scalar_one_or_none()

    async def next_sequence(self, session_id: uuid.UUID, analysis_type: AnalysisType) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(EvidenceBatch.sequence_number), 0) + 1).where(
                EvidenceBatch.session_id == session_id,
                EvidenceBatch.analysis_type == analysis_type,
            )
        )
        return int(result.scalar_one())

    async def list_for_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[EvidenceBatch]:
        query = (
            select(EvidenceBatch)
            .join(TradeSession, EvidenceBatch.session_id == TradeSession.id)
            .where(EvidenceBatch.session_id == session_id, TradeSession.owner_id == user_id)
            .order_by(EvidenceBatch.sequence_number.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return result.unique().scalars().all()
