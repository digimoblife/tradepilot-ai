from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import ProviderType

if TYPE_CHECKING:
    from app.models.analysis_job import AnalysisJob
    from app.models.provider_response import ProviderResponse


class ProviderRequest(Base):
    __tablename__ = "provider_requests"

    __table_args__ = (
        CheckConstraint("attempt_number >= 1", name="attempt_number"),
        CheckConstraint(
            "prompt_name IS NOT NULL AND BTRIM(prompt_name) <> ''",
            name="prompt_name",
        ),
        CheckConstraint(
            "prompt_version IS NOT NULL AND BTRIM(prompt_version) <> ''",
            name="prompt_version",
        ),
        CheckConstraint(
            "schema_name IS NOT NULL AND BTRIM(schema_name) <> ''",
            name="schema_name",
        ),
        CheckConstraint(
            "schema_version IS NOT NULL AND BTRIM(schema_version) <> ''",
            name="schema_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(), primary_key=True, default=uuid.uuid4
    )
    analysis_job_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[ProviderType] = mapped_column(
        SAEnum(ProviderType, name="provider_enum"),
        nullable=False,
    )
    provider_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prompt_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    request_metadata: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    analysis_job: Mapped[AnalysisJob] = relationship(
        back_populates="provider_requests",
    )
    responses: Mapped[list[ProviderResponse]] = relationship(
        back_populates="provider_request",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("attempt_number", 1)
        kwargs.setdefault("requested_at", func.now())
        kwargs.setdefault("created_at", func.now())
        super().__init__(**kwargs)
