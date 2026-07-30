from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.trade_session import (
    TradeSessionV2,
    TradeSessionV2Status,
)

_AVAILABLE_ACTIONS: dict[TradeSessionV2Status, tuple[str, ...]] = {
    TradeSessionV2Status.ANALYZED: ("BUY", "WAIT", "SKIP"),
    TradeSessionV2Status.WAITING: ("BUY", "WAIT", "SKIP"),
    TradeSessionV2Status.OPEN_POSITION: ("CLOSE",),
    TradeSessionV2Status.DRAFT: (),
    TradeSessionV2Status.ANALYZING: (),
    TradeSessionV2Status.CLOSED: (),
    TradeSessionV2Status.CLOSED_SKIPPED: (),
}


@dataclass(frozen=True, slots=True)
class DecisionAvailability:
    session_id: uuid.UUID
    session_status: TradeSessionV2Status
    available_actions: tuple[str, ...]


class DecisionAvailabilityService:
    """Read-only action availability for one owned rebuild session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_owned(
        self, *, user_id: uuid.UUID, session_id: uuid.UUID
    ) -> DecisionAvailability | None:
        trade_session = await self._session.scalar(
            select(TradeSessionV2).where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
        )
        if trade_session is None:
            return None
        return DecisionAvailability(
            session_id=trade_session.id,
            session_status=trade_session.status,
            available_actions=_AVAILABLE_ACTIONS[trade_session.status],
        )
