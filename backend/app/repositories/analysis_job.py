from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob
from app.models.enums import AnalysisJobStatus
from app.models.trade_session import TradeSession


_STATUSES_TERMINAL = frozenset(
    {
        AnalysisJobStatus.COMPLETED,
        AnalysisJobStatus.FAILED,
        AnalysisJobStatus.CANCELLED,
    }
)


class AnalysisJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: AnalysisJob) -> AnalysisJob:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_id_for_user(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> AnalysisJob | None:
        result = await self._session.execute(
            select(AnalysisJob)
            .join(TradeSession, AnalysisJob.session_id == TradeSession.id)
            .where(
                AnalysisJob.id == job_id,
                TradeSession.owner_id == user_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_by_id_for_user_for_update(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> AnalysisJob | None:
        result = await self._session.execute(
            select(AnalysisJob)
            .join(TradeSession, AnalysisJob.session_id == TradeSession.id)
            .where(
                AnalysisJob.id == job_id,
                TradeSession.owner_id == user_id,
            )
            .with_for_update()
        )
        return result.unique().scalar_one_or_none()

    async def list_for_session_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[AnalysisJob]:
        query = (
            select(AnalysisJob)
            .join(TradeSession, AnalysisJob.session_id == TradeSession.id)
            .where(
                AnalysisJob.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
            .order_by(AnalysisJob.requested_at, AnalysisJob.id)
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return result.unique().scalars().all()

    async def find_active_for_session_and_type_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        analysis_type: str,
    ) -> AnalysisJob | None:
        result = await self._session.execute(
            select(AnalysisJob)
            .join(TradeSession, AnalysisJob.session_id == TradeSession.id)
            .where(
                AnalysisJob.session_id == session_id,
                TradeSession.owner_id == user_id,
                AnalysisJob.analysis_type == analysis_type,
                AnalysisJob.status.not_in(_STATUSES_TERMINAL),
            )
            .order_by(AnalysisJob.requested_at.desc(), AnalysisJob.id.desc())
            .limit(1)
        )
        return result.unique().scalar_one_or_none()
