from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


class RebuildTradeSessionService:
    """Persistence operations for the rebuild-owned session API."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        ticker: str,
        company_name: str,
        note: str | None,
    ) -> TradeSessionV2:
        normalized_ticker = ticker.strip().upper()
        normalized_company_name = company_name.strip()
        if not normalized_ticker or not normalized_company_name:
            raise ValueError("Ticker and company name must not be blank")

        trade_session = TradeSessionV2(
            user_id=user_id,
            ticker=normalized_ticker,
            company_name=normalized_company_name,
            note=note,
            status=TradeSessionV2Status.DRAFT,
            closed_at=None,
        )
        self._session.add(trade_session)
        await self._session.flush()
        return trade_session

    async def list_owned(self, *, user_id: uuid.UUID) -> list[TradeSessionV2]:
        result = await self._session.scalars(
            select(TradeSessionV2)
            .where(TradeSessionV2.user_id == user_id)
            .order_by(TradeSessionV2.created_at.desc(), TradeSessionV2.id.desc())
        )
        return list(result.all())

    async def get_owned(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TradeSessionV2 | None:
        return await self._session.scalar(
            select(TradeSessionV2).where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
        )
