from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trade_session import TradeSession


class TradeSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: TradeSession) -> TradeSession:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_id_for_user(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradeSession | None:
        result = await self._session.execute(
            select(TradeSession).where(
                TradeSession.id == session_id,
                TradeSession.owner_id == user_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_by_id_for_user_for_update(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradeSession | None:
        result = await self._session.execute(
            select(TradeSession)
            .where(
                TradeSession.id == session_id,
                TradeSession.owner_id == user_id,
            )
            .with_for_update()
        )
        return result.unique().scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[TradeSession]:
        query = (
            select(TradeSession)
            .where(TradeSession.owner_id == user_id)
            .order_by(TradeSession.updated_at.desc(), TradeSession.id)
        )
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        result = await self._session.execute(query)
        return result.unique().scalars().all()

    async def exists_for_user(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(func.count(TradeSession.id)).where(
                TradeSession.id == session_id,
                TradeSession.owner_id == user_id,
            )
        )
        count = result.scalar_one()
        return count > 0
