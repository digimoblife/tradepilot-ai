from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import pg_uuid, price_numeric, utc_datetime


class AnalysisRequestV2Type(str, enum.Enum):
    INITIAL_ANALYSIS = "INITIAL_ANALYSIS"
    WAIT_UPDATE = "WAIT_UPDATE"
    POSITION_UPDATE = "POSITION_UPDATE"


class AnalysisRequestV2ObservationPeriod(str, enum.Enum):
    MORNING = "MORNING"
    MIDDAY = "MIDDAY"
    AFTERNOON = "AFTERNOON"


class AnalysisRequestV2Status(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisRequestV2(Base):
    __tablename__ = "analysis_requests_v2"

    __table_args__ = (
        CheckConstraint("current_price IS NULL OR current_price > 0", name="price_positive"),
        CheckConstraint("provider = 'gemini'", name="provider_gemini_only"),
        CheckConstraint(
            """
            analysis_type = 'INITIAL_ANALYSIS'
            OR (
                current_price IS NOT NULL
                AND observation_period IS NOT NULL
                AND observation_at IS NOT NULL
            )
            """,
            name="observation_fields_required",
        ),
        Index("ix_analysis_requests_v2_session_id", "session_id"),
        Index("ix_analysis_requests_v2_status", "status"),
        Index("ix_analysis_requests_v2_analysis_type", "analysis_type"),
        Index("ix_analysis_requests_v2_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
        nullable=False,
    )
    analysis_type: Mapped[AnalysisRequestV2Type] = mapped_column(
        SAEnum(AnalysisRequestV2Type, name="analysis_request_v2_type_enum", native_enum=True),
        nullable=False,
    )
    observation_period: Mapped[AnalysisRequestV2ObservationPeriod | None] = mapped_column(
        SAEnum(
            AnalysisRequestV2ObservationPeriod,
            name="analysis_request_v2_observation_period_enum",
            native_enum=True,
        ),
        nullable=True,
    )
    current_price: Mapped[Decimal | None] = mapped_column(price_numeric(), nullable=True)
    observation_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    status: Mapped[AnalysisRequestV2Status] = mapped_column(
        SAEnum(AnalysisRequestV2Status, name="analysis_request_v2_status_enum", native_enum=True),
        nullable=False,
        default=AnalysisRequestV2Status.PENDING,
        server_default=AnalysisRequestV2Status.PENDING.value,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    raw_response: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    processed_response: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
