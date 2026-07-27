from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import AnalysisType, EvidenceBatchStatus

if TYPE_CHECKING:
    from app.models.analysis_job import AnalysisJob
    from app.models.evidence import Evidence
    from app.models.trade_session import TradeSession
    from app.models.user import User


class EvidenceBatch(Base):
    __tablename__ = "evidence_batches"

    __table_args__ = (
        CheckConstraint("sequence_number > 0", name="evidence_batch_sequence_positive"),
        UniqueConstraint(
            "session_id",
            "analysis_type",
            "sequence_number",
            name="uq_evidence_batches_session_analysis_sequence",
        ),
        Index("ix_evidence_batches_session_created", "session_id", "created_at"),
        Index("ix_evidence_batches_session_status", "session_id", "status"),
        Index(
            "uq_evidence_batches_one_draft_per_session_analysis",
            "session_id",
            "analysis_type",
            unique=True,
            postgresql_where=text("status = 'DRAFT'::evidence_batch_status_enum"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    analysis_type: Mapped[AnalysisType] = mapped_column(
        SAEnum(AnalysisType, name="analysis_type_enum"),
        nullable=False,
    )
    status: Mapped[EvidenceBatchStatus] = mapped_column(
        SAEnum(EvidenceBatchStatus, name="evidence_batch_status_enum"),
        default=EvidenceBatchStatus.DRAFT,
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    processing_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    trade_session: Mapped[TradeSession] = relationship(back_populates="evidence_batches")
    owner: Mapped[User] = relationship(back_populates="evidence_batches")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="evidence_batch")
    analysis_jobs: Mapped[list[AnalysisJob]] = relationship(back_populates="evidence_batch")

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("status", EvidenceBatchStatus.DRAFT)
        kwargs.setdefault("created_at", func.now())
        kwargs.setdefault("updated_at", func.now())
        super().__init__(**kwargs)
