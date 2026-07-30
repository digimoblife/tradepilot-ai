from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import pg_uuid, price_numeric, quantity_numeric, utc_datetime


class PositionV2Status(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class PositionV2(Base):
    __tablename__ = "positions_v2"

    __table_args__ = (
        CheckConstraint("entry_price > 0", name="entry_price_positive"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("stop_loss > 0", name="stop_loss_positive"),
        CheckConstraint("target_price > 0", name="target_price_positive"),
        Index("uq_positions_v2_session_id", "session_id", unique=True),
        Index("ix_positions_v2_status", "status"),
        Index("ix_positions_v2_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entry_price: Mapped[Decimal] = mapped_column(price_numeric(), nullable=False)
    entry_at: Mapped[datetime] = mapped_column(utc_datetime(), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(quantity_numeric(), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(price_numeric(), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(price_numeric(), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PositionV2Status] = mapped_column(
        SAEnum(PositionV2Status, name="position_v2_status_enum", native_enum=True),
        nullable=False,
        default=PositionV2Status.OPEN,
        server_default=PositionV2Status.OPEN.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
