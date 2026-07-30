from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import monetary_numeric, pg_uuid, price_numeric, utc_datetime


class TradeClosureV2(Base):
    __tablename__ = "trade_closures_v2"

    __table_args__ = (
        CheckConstraint("close_price > 0", name="close_price_positive"),
        CheckConstraint("length(btrim(close_reason)) > 0", name="close_reason_not_blank"),
        Index("ix_trade_closures_v2_session_id", "session_id"),
        Index("uq_trade_closures_v2_position_id", "position_id", unique=True),
        Index("ix_trade_closures_v2_close_at", "close_at"),
        Index("ix_trade_closures_v2_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("positions_v2.id", ondelete="RESTRICT"),
        nullable=False,
    )
    close_price: Mapped[Decimal] = mapped_column(price_numeric(), nullable=False)
    close_at: Mapped[datetime] = mapped_column(utc_datetime(), nullable=False)
    close_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    realized_profit_loss: Mapped[Decimal] = mapped_column(monetary_numeric(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
