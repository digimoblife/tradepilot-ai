from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import pg_uuid, price_numeric, utc_datetime
from app.trade_workspace.models.analysis_request import AnalysisRequestV2ObservationPeriod


class EvidenceUploadV2Type(str, enum.Enum):
    ORDERBOOK = "ORDERBOOK"
    CHART_3_MONTH = "CHART_3_MONTH"
    CHART_6_MONTH = "CHART_6_MONTH"
    FOREIGN_FLOW_1W = "FOREIGN_FLOW_1W"
    BROKER_FLOW_1D = "BROKER_FLOW_1D"


class EvidenceUploadV2(Base):
    __tablename__ = "evidence_uploads_v2"

    __table_args__ = (
        CheckConstraint("length(btrim(file_path)) > 0", name="file_path_not_blank"),
        CheckConstraint(
            "length(btrim(original_filename)) > 0",
            name="original_filename_not_blank",
        ),
        CheckConstraint("length(btrim(mime_type)) > 0", name="mime_type_not_blank"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        Index("ix_evidence_uploads_v2_session_id", "session_id"),
        Index("ix_evidence_uploads_v2_analysis_request_id", "analysis_request_id"),
        Index("ix_evidence_uploads_v2_evidence_type", "evidence_type"),
        Index("ix_evidence_uploads_v2_uploaded_at", "uploaded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
        nullable=False,
    )
    analysis_request_id: Mapped[uuid.UUID | None] = mapped_column(
        pg_uuid(),
        ForeignKey("analysis_requests_v2.id", ondelete="RESTRICT"),
        nullable=True,
    )
    evidence_type: Mapped[EvidenceUploadV2Type] = mapped_column(
        SAEnum(EvidenceUploadV2Type, name="evidence_upload_v2_type_enum", native_enum=True),
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
    observation_timestamp: Mapped[datetime | None] = mapped_column(
        utc_datetime(), nullable=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
