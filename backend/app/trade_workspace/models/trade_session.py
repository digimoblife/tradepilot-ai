from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime


class TradeSessionV2Status(str, enum.Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    WAITING = "WAITING"
    OPEN_POSITION = "OPEN_POSITION"
    CLOSED = "CLOSED"
    CLOSED_SKIPPED = "CLOSED_SKIPPED"


class TradeSessionV2(Base):
    __tablename__ = "trade_sessions_v2"

    __table_args__ = (
        CheckConstraint("length(btrim(ticker)) > 0", name="ticker_not_blank"),
        CheckConstraint("length(btrim(company_name)) > 0", name="company_name_not_blank"),
        Index("ix_trade_sessions_v2_user_id", "user_id"),
        Index("ix_trade_sessions_v2_status", "status"),
        Index("ix_trade_sessions_v2_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TradeSessionV2Status] = mapped_column(
        SAEnum(
            TradeSessionV2Status,
            name="trade_session_v2_status_enum",
            native_enum=True,
        ),
        nullable=False,
        default=TradeSessionV2Status.DRAFT,
        server_default=TradeSessionV2Status.DRAFT.value,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)

    def __init__(self, **kwargs: object) -> None:
        if "ticker" in kwargs:
            kwargs["ticker"] = str(kwargs["ticker"]).strip().upper()
        if "company_name" in kwargs:
            kwargs["company_name"] = str(kwargs["company_name"]).strip()
        kwargs.setdefault("status", TradeSessionV2Status.DRAFT)
        super().__init__(**kwargs)
