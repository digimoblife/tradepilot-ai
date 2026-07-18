from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, nullslast
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.models.trade_session import TradeSession
from app.models.enums import EvidenceStatus


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: Evidence) -> Evidence:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_id_for_user(
        self, evidence_id: uuid.UUID, user_id: uuid.UUID
    ) -> Evidence | None:
        result = await self._session.execute(
            select(Evidence)
            .join(TradeSession, Evidence.session_id == TradeSession.id)
            .where(
                Evidence.id == evidence_id,
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
    ) -> Sequence[Evidence]:
        query = (
            select(Evidence)
            .join(TradeSession, Evidence.session_id == TradeSession.id)
            .where(
                Evidence.session_id == session_id,
                TradeSession.owner_id == user_id,
            )
            .order_by(
                nullslast(Evidence.market_timestamp.desc()),
                Evidence.uploaded_at.desc(),
                Evidence.id,
            )
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return result.unique().scalars().all()

    async def list_active_for_session_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[Evidence]:
        query = (
            select(Evidence)
            .join(TradeSession, Evidence.session_id == TradeSession.id)
            .where(
                Evidence.session_id == session_id,
                TradeSession.owner_id == user_id,
                Evidence.evidence_status == EvidenceStatus.AVAILABLE,
                Evidence.deleted_at.is_(None),
            )
            .order_by(
                nullslast(Evidence.market_timestamp.desc()),
                Evidence.uploaded_at.desc(),
                Evidence.id,
            )
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return result.unique().scalars().all()

    async def get_latest_active_by_type_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        evidence_type: str,
    ) -> Evidence | None:
        result = await self._session.execute(
            select(Evidence)
            .join(TradeSession, Evidence.session_id == TradeSession.id)
            .where(
                Evidence.session_id == session_id,
                TradeSession.owner_id == user_id,
                Evidence.evidence_type == evidence_type,
                Evidence.evidence_status == EvidenceStatus.AVAILABLE,
                Evidence.deleted_at.is_(None),
            )
            .order_by(
                nullslast(Evidence.market_timestamp.desc()),
                Evidence.uploaded_at.desc(),
                Evidence.id,
            )
            .limit(1)
        )
        return result.unique().scalar_one_or_none()
