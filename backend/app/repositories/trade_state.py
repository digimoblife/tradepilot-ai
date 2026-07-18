from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade_session import TradeSession
from app.models.trade_state import TradeState


class TradeStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: TradeState) -> TradeState:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_for_user(self, session_id: uuid.UUID, user_id: uuid.UUID) -> TradeState | None:
        result = await self._session.execute(
            select(TradeState)
            .join(TradeSession, TradeState.session_id == TradeSession.id)
            .where(
                TradeState.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_for_user_for_update(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradeState | None:
        result = await self._session.execute(
            select(TradeState)
            .join(TradeSession, TradeState.session_id == TradeSession.id)
            .where(
                TradeState.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
            .with_for_update()
        )
        return result.unique().scalar_one_or_none()
