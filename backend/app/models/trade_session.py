from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import Currency, Market, TradeSessionStatus

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.analysis_job import AnalysisJob
    from app.models.context_summary import ContextSummary
    from app.models.evidence import Evidence
    from app.models.session_event import SessionEvent
    from app.models.trade_action import TradeAction
    from app.models.trade_state import TradeState
    from app.models.user import User


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def normalize_currency(currency: str) -> str:
    return currency.strip().upper()


class TradeSession(Base):
    __tablename__ = "trade_sessions"

    __table_args__ = (
        Index("ix_trade_sessions_ticker", "ticker"),
        Index(
            "ix_trade_sessions_owner_lifecycle",
            "owner_id",
            "lifecycle_status",
        ),
        Index(
            "ix_trade_sessions_owner_updated",
            "owner_id",
            text("updated_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market: Mapped[Market] = mapped_column(
        SAEnum(Market, name="market_enum"),
        default=Market.IDX,
        nullable=False,
    )
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency_enum"),
        default=Currency.IDR,
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    initial_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[TradeSessionStatus] = mapped_column(
        SAEnum(TradeSessionStatus, name="session_status_enum"),
        default=TradeSessionStatus.DRAFT,
        nullable=False,
    )
    stable_status: Mapped[TradeSessionStatus] = mapped_column(
        SAEnum(TradeSessionStatus, name="session_status_enum"),
        default=TradeSessionStatus.DRAFT,
        nullable=False,
    )
    pre_archive_status: Mapped[TradeSessionStatus | None] = mapped_column(
        SAEnum(TradeSessionStatus, name="session_status_enum"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)

    user: Mapped[User] = relationship(
        back_populates="trade_sessions",
    )
    trade_state: Mapped[TradeState | None] = relationship(
        back_populates="trade_session",
        uselist=False,
    )
    trade_actions: Mapped[list[TradeAction]] = relationship(
        back_populates="trade_session",
    )
    evidence_items: Mapped[list[Evidence]] = relationship(
        back_populates="trade_session",
    )
    analysis_jobs: Mapped[list[AnalysisJob]] = relationship(
        back_populates="trade_session",
    )
    analyses: Mapped[list[Analysis]] = relationship(
        back_populates="trade_session",
    )
    context_summaries: Mapped[list[ContextSummary]] = relationship(
        back_populates="trade_session",
    )
    session_events: Mapped[list[SessionEvent]] = relationship(
        back_populates="trade_session",
    )

    def __init__(self, **kwargs: object) -> None:
        if "ticker" in kwargs:
            kwargs["ticker"] = normalize_ticker(str(kwargs["ticker"]))
        if "currency" in kwargs:
            kwargs["currency"] = normalize_currency(str(kwargs["currency"]))
        kwargs.setdefault("lifecycle_status", TradeSessionStatus.DRAFT)
        kwargs.setdefault("stable_status", TradeSessionStatus.DRAFT)
        kwargs.setdefault("market", Market.IDX)
        kwargs.setdefault("currency", Currency.IDR)
        kwargs.setdefault("version", 1)
        kwargs.setdefault("created_at", func.now())
        kwargs.setdefault("updated_at", func.now())
        super().__init__(**kwargs)
