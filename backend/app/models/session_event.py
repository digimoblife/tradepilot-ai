from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, price_numeric, quantity_numeric, utc_datetime
from app.models.enums import SessionEventType

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.trade_action import TradeAction
    from app.models.trade_session import TradeSession


class SessionEvent(Base):
    __tablename__ = "session_events"

    __table_args__ = (
        CheckConstraint("quantity IS NULL OR quantity >= 0", name="quantity"),
        Index(
            "ix_session_events_chronological",
            "session_id",
            "occurred_at",
            "id",
        ),
        Index(
            "ix_session_events_related_action",
            "related_action_id",
        ),
        Index(
            "ix_session_events_related_analysis",
            "related_analysis_id",
        ),
        Index(
            "ix_session_events_type",
            "event_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[SessionEventType] = mapped_column(
        SAEnum(SessionEventType, name="session_event_type_enum"),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(utc_datetime(), nullable=False)
    related_action_id: Mapped[uuid.UUID | None] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_actions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    related_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        pg_uuid(),
        ForeignKey("analyses.id", ondelete="RESTRICT"),
        nullable=True,
    )
    price: Mapped[Decimal | None] = mapped_column(price_numeric(), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(quantity_numeric(), nullable=True)
    compact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    trade_session: Mapped[TradeSession] = relationship(
        back_populates="session_events",
    )
    related_action: Mapped[TradeAction | None] = relationship(
        back_populates="session_events",
    )
    related_analysis: Mapped[Analysis | None] = relationship(
        back_populates="session_events",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("created_at", func.now())
        super().__init__(**kwargs)
