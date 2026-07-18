from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session_event import SessionEvent
from app.models.trade_session import TradeSession


class SessionEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: SessionEvent) -> SessionEvent:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_id_for_user(
        self, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> SessionEvent | None:
        result = await self._session.execute(
            select(SessionEvent)
            .join(TradeSession, SessionEvent.session_id == TradeSession.id)
            .where(
                SessionEvent.id == event_id,
                TradeSession.owner_id == user_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def list_for_session_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        event_type: str | None = None,
        occurred_after: datetime | None = None,
        occurred_before: datetime | None = None,
        limit: int | None = None,
    ) -> Sequence[SessionEvent]:
        query = (
            select(SessionEvent)
            .join(TradeSession, SessionEvent.session_id == TradeSession.id)
            .where(
                SessionEvent.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
            .order_by(SessionEvent.occurred_at, SessionEvent.id)
        )
        if event_type is not None:
            query = query.where(SessionEvent.event_type == event_type)
        if occurred_after is not None:
            query = query.where(SessionEvent.occurred_at >= occurred_after)
        if occurred_before is not None:
            query = query.where(SessionEvent.occurred_at <= occurred_before)
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return result.unique().scalars().all()
