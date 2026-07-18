from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context_summary import ContextSummary
from app.models.trade_session import TradeSession


class ContextSummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: ContextSummary) -> ContextSummary:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_id_for_user(
        self, summary_id: uuid.UUID, user_id: uuid.UUID
    ) -> ContextSummary | None:
        result = await self._session.execute(
            select(ContextSummary)
            .join(TradeSession, ContextSummary.session_id == TradeSession.id)
            .where(
                ContextSummary.id == summary_id,
                TradeSession.owner_id == user_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def list_versions_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[ContextSummary]:
        query = (
            select(ContextSummary)
            .join(TradeSession, ContextSummary.session_id == TradeSession.id)
            .where(
                ContextSummary.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
            .order_by(ContextSummary.context_version.asc(), ContextSummary.id)
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return result.unique().scalars().all()

    async def get_latest_for_user(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> ContextSummary | None:
        result = await self._session.execute(
            select(ContextSummary)
            .join(TradeSession, ContextSummary.session_id == TradeSession.id)
            .where(
                ContextSummary.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
            .order_by(ContextSummary.context_version.desc(), ContextSummary.id.desc())
            .limit(1)
        )
        return result.unique().scalar_one_or_none()

    async def get_latest_non_stale_for_user(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> ContextSummary | None:
        result = await self._session.execute(
            select(ContextSummary)
            .join(TradeSession, ContextSummary.session_id == TradeSession.id)
            .where(
                ContextSummary.session_id == session_id,
                TradeSession.owner_id == user_id,
                ContextSummary.is_stale.is_(False),
            )
            .order_by(ContextSummary.context_version.desc(), ContextSummary.id.desc())
            .limit(1)
        )
        return result.unique().scalar_one_or_none()
