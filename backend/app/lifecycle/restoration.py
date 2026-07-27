"""Shared lifecycle restoration helpers for analysis job failures."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TradeSessionStatus
from app.models.trade_session import TradeSession


def parse_restorable_status(value: str | None) -> TradeSessionStatus | None:
    if not value:
        return None
    try:
        return TradeSessionStatus(value)
    except ValueError:
        return None


async def restore_session_status(
    session: AsyncSession,
    trade_session: TradeSession,
    previous_status: str | None,
) -> TradeSessionStatus | None:
    restored = parse_restorable_status(previous_status)
    if restored is None:
        return None
    trade_session.lifecycle_status = restored
    trade_session.stable_status = restored
    await session.flush()
    return restored
