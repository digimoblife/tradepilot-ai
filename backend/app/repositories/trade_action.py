from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade_action import TradeAction
from app.models.trade_session import TradeSession


class TradeActionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: TradeAction) -> TradeAction:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_id_for_user(
        self, action_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradeAction | None:
        result = await self._session.execute(
            select(TradeAction)
            .join(TradeSession, TradeAction.session_id == TradeSession.id)
            .where(
                TradeAction.id == action_id,
                TradeSession.owner_id == user_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_by_idempotency_key_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        idempotency_key: str,
    ) -> TradeAction | None:
        result = await self._session.execute(
            select(TradeAction)
            .join(TradeSession, TradeAction.session_id == TradeSession.id)
            .where(
                TradeAction.session_id == session_id,
                TradeAction.idempotency_key == idempotency_key,
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
    ) -> Sequence[TradeAction]:
        query = (
            select(TradeAction)
            .join(TradeSession, TradeAction.session_id == TradeSession.id)
            .where(
                TradeAction.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
            .order_by(TradeAction.confirmed_at, TradeAction.created_at, TradeAction.id)
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return result.unique().scalars().all()
