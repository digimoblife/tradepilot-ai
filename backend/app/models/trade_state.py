from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import (
    monetary_numeric,
    pg_uuid,
    price_numeric,
    return_pct_numeric,
    utc_datetime,
)
from app.models.enums import PositionStatus, ThesisStatus

if TYPE_CHECKING:
    from app.models.trade_session import TradeSession


class TradeState(Base):
    __tablename__ = "trade_states"

    __table_args__ = (
        CheckConstraint(
            "original_quantity IS NULL OR original_quantity >= 0",
            name="ck_original_quantity_non_negative",
        ),
        CheckConstraint(
            "remaining_quantity IS NULL OR remaining_quantity >= 0",
            name="ck_remaining_quantity_non_negative",
        ),
        CheckConstraint(
            "original_quantity IS NULL OR remaining_quantity IS NULL "
            "OR remaining_quantity <= original_quantity",
            name="ck_remaining_not_above_original",
        ),
        CheckConstraint(
            "state_version >= 1",
            name="ck_state_version_min",
        ),
        Index(
            "ix_trade_states_position_status",
            "position_status",
        ),
        Index(
            "ix_trade_states_entry_at",
            text("entry_at DESC"),
        ),
        Index(
            "ix_trade_states_session_status",
            "position_status",
            "session_id",
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position_status: Mapped[PositionStatus] = mapped_column(
        SAEnum(PositionStatus, name="position_status_enum"),
        default=PositionStatus.NOT_OPENED,
        nullable=False,
    )
    thesis_status: Mapped[ThesisStatus] = mapped_column(
        SAEnum(ThesisStatus, name="thesis_status_enum"),
        default=ThesisStatus.INTACT,
        nullable=False,
    )
    entry_price: Mapped[Decimal | None] = mapped_column(price_numeric(), nullable=True)
    entry_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    original_quantity: Mapped[Decimal | None] = mapped_column(monetary_numeric(), nullable=True)
    remaining_quantity: Mapped[Decimal | None] = mapped_column(monetary_numeric(), nullable=True)
    active_stop_loss: Mapped[Decimal | None] = mapped_column(price_numeric(), nullable=True)
    active_target: Mapped[Decimal | None] = mapped_column(price_numeric(), nullable=True)
    average_exit_price: Mapped[Decimal | None] = mapped_column(price_numeric(), nullable=True)
    realized_pnl: Mapped[Decimal | None] = mapped_column(monetary_numeric(), nullable=True)
    realized_return: Mapped[Decimal | None] = mapped_column(return_pct_numeric(), nullable=True)
    last_confirmed_action_at: Mapped[datetime | None] = mapped_column(
        utc_datetime(), nullable=True
    )
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    trade_session: Mapped[TradeSession] = relationship(
        back_populates="trade_state",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("position_status", PositionStatus.NOT_OPENED)
        kwargs.setdefault("thesis_status", ThesisStatus.INTACT)
        kwargs.setdefault("state_version", 1)
        kwargs.setdefault("created_at", func.now())
        kwargs.setdefault("updated_at", func.now())
        super().__init__(**kwargs)
