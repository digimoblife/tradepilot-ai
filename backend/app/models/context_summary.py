from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import ContextQuality

if TYPE_CHECKING:
    from app.models.trade_session import TradeSession


class ContextSummary(Base):
    __tablename__ = "context_summaries"

    __table_args__ = (
        CheckConstraint("context_version >= 1", name="version"),
        UniqueConstraint(
            "session_id",
            "context_version",
            name="uq_context_summaries_session_version",
        ),
        Index(
            "ix_context_summaries_session_version",
            "session_id",
            text("context_version DESC"),
        ),
        Index(
            "ix_context_summaries_session_created",
            "session_id",
            text("created_at DESC"),
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
    context_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_cutoff: Mapped[datetime | None] = mapped_column(
        utc_datetime(), nullable=True
    )
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    quality: Mapped[ContextQuality] = mapped_column(
        SAEnum(ContextQuality, name="context_quality_enum"),
        default=ContextQuality.HIGH,
        nullable=False,
    )
    is_stale: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    trade_session: Mapped[TradeSession] = relationship(
        back_populates="context_summaries",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("quality", ContextQuality.HIGH)
        kwargs.setdefault("is_stale", False)
        kwargs.setdefault("created_at", func.now())
        super().__init__(**kwargs)
