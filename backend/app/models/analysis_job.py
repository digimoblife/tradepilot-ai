from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import AnalysisJobStatus, AnalysisType

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.provider_request import ProviderRequest
    from app.models.trade_session import TradeSession
    from app.models.validation_attempt import ValidationAttempt


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="attempt_count"),
        CheckConstraint("max_attempts > 0", name="max_attempts"),
        CheckConstraint("attempt_count <= max_attempts", name="attempts_bound"),
        Index(
            "ix_analysis_jobs_queue",
            "status",
            "available_at",
        ),
        Index(
            "ix_analysis_jobs_lease",
            "status",
            "lease_expires_at",
        ),
        Index(
            "ix_analysis_jobs_session_created",
            "session_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_analysis_jobs_session_type_status",
            "session_id",
            "analysis_type",
            "status",
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
    analysis_type: Mapped[AnalysisType] = mapped_column(
        SAEnum(AnalysisType, name="analysis_type_enum"),
        nullable=False,
    )
    status: Mapped[AnalysisJobStatus] = mapped_column(
        SAEnum(AnalysisJobStatus, name="analysis_job_status_enum"),
        default=AnalysisJobStatus.CREATED,
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    previous_session_status: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    available_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    lease_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lease_acquired_at: Mapped[datetime | None] = mapped_column(
        utc_datetime(), nullable=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        utc_datetime(), nullable=True
    )
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    trade_session: Mapped[TradeSession] = relationship(
        back_populates="analysis_jobs",
    )
    provider_requests: Mapped[list[ProviderRequest]] = relationship(
        back_populates="analysis_job",
    )
    analysis: Mapped[Analysis | None] = relationship(
        back_populates="analysis_job",
        uselist=False,
    )
    validation_attempts: Mapped[list[ValidationAttempt]] = relationship(
        back_populates="analysis_job",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("status", AnalysisJobStatus.CREATED)
        kwargs.setdefault("attempt_count", 0)
        kwargs.setdefault("max_attempts", 3)
        kwargs.setdefault("requested_at", func.now())
        kwargs.setdefault("available_at", func.now())
        kwargs.setdefault("created_at", func.now())
        kwargs.setdefault("updated_at", func.now())
        super().__init__(**kwargs)
