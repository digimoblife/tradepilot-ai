from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, price_numeric, quantity_numeric, utc_datetime
from app.models.enums import ActionType

if TYPE_CHECKING:
    from app.models.trade_session import TradeSession


def _default_payload() -> dict[str, object]:
    return {}


class TradeAction(Base):
    __tablename__ = "trade_actions"

    __table_args__ = (
        CheckConstraint(
            "quantity IS NULL OR quantity >= 0",
            name="quantity_non_negative",
        ),
        Index(
            "ix_trade_actions_session_confirmed",
            "session_id",
            "confirmed_at",
        ),
        Index(
            "ix_trade_actions_session_type",
            "session_id",
            "action_type",
        ),
        Index(
            "ix_trade_actions_idempotency",
            "session_id",
            "idempotency_key",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[ActionType] = mapped_column(
        SAEnum(ActionType, name="trade_action_type_enum"),
        nullable=False,
    )
    confirmed_at: Mapped[datetime] = mapped_column(utc_datetime(), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(price_numeric(), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(quantity_numeric(), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        pg_uuid(), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=_default_payload
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    trade_session: Mapped[TradeSession] = relationship(
        back_populates="trade_actions",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("payload", {})
        kwargs.setdefault("created_at", func.now())
        super().__init__(**kwargs)
