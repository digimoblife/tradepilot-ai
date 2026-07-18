from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.enums import AcceptanceStatus
from app.models.trade_session import TradeSession


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: Analysis) -> Analysis:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_id_for_user(
        self, analysis_id: uuid.UUID, user_id: uuid.UUID
    ) -> Analysis | None:
        result = await self._session.execute(
            select(Analysis)
            .join(TradeSession, Analysis.session_id == TradeSession.id)
            .where(
                Analysis.id == analysis_id,
                TradeSession.owner_id == user_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def list_for_session_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[Analysis]:
        query = (
            select(Analysis)
            .join(TradeSession, Analysis.session_id == TradeSession.id)
            .where(
                Analysis.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
            .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return result.unique().scalars().all()

    async def get_latest_accepted_for_user(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> Analysis | None:
        result = await self._session.execute(
            select(Analysis)
            .join(TradeSession, Analysis.session_id == TradeSession.id)
            .where(
                Analysis.session_id == session_id,
                TradeSession.owner_id == user_id,
                Analysis.acceptance_status == AcceptanceStatus.ACCEPTED,
            )
            .order_by(
                Analysis.accepted_at.desc(),
                Analysis.created_at.desc(),
                Analysis.id.desc(),
            )
            .limit(1)
        )
        return result.unique().scalar_one_or_none()

    async def get_latest_accepted_by_type_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        analysis_type: str,
    ) -> Analysis | None:
        result = await self._session.execute(
            select(Analysis)
            .join(TradeSession, Analysis.session_id == TradeSession.id)
            .where(
                Analysis.session_id == session_id,
                TradeSession.owner_id == user_id,
                Analysis.acceptance_status == AcceptanceStatus.ACCEPTED,
                Analysis.analysis_type == analysis_type,
            )
            .order_by(
                Analysis.accepted_at.desc(),
                Analysis.created_at.desc(),
                Analysis.id.desc(),
            )
            .limit(1)
        )
        return result.unique().scalar_one_or_none()
