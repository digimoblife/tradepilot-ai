from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import ValidationStage

if TYPE_CHECKING:
    from app.models.analysis_job import AnalysisJob
    from app.models.provider_response import ProviderResponse


class ValidationAttempt(Base):
    __tablename__ = "validation_attempts"

    __table_args__ = (CheckConstraint("attempt_number >= 1", name="attempt_number"),)

    id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(), primary_key=True, default=uuid.uuid4
    )
    analysis_job_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider_response_id: Mapped[uuid.UUID | None] = mapped_column(
        pg_uuid(),
        ForeignKey("provider_responses.id", ondelete="RESTRICT"),
        nullable=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stage: Mapped[ValidationStage] = mapped_column(
        SAEnum(ValidationStage, name="validation_stage_enum"),
        nullable=False,
    )
    valid: Mapped[bool] = mapped_column(nullable=False)
    issues: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    parsed_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    validated_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    analysis_job: Mapped[AnalysisJob] = relationship(
        back_populates="validation_attempts",
    )
    provider_response: Mapped[ProviderResponse | None] = relationship(
        back_populates="validation_attempts",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("attempt_number", 1)
        kwargs.setdefault("created_at", func.now())
        super().__init__(**kwargs)
