"""Evaluation record domain model (P7).

Represents a compact canonical evaluation record linking prediction, user decision,
and trade outcome fields for offline evaluation, prompt comparison, and auditability.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CompletenessStatus(str, enum.Enum):
    """Data completeness status for evaluation records."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    LEGACY_PARTIAL = "LEGACY_PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class EvaluationRecord(Base):
    """Canonical structured evaluation record linking predictions, user decisions, and outcomes."""

    __tablename__ = "evaluation_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trade_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evidence_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    prompt_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    schema_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)

    prediction_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    user_decision_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    outcome_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    completeness_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CompletenessStatus.PARTIAL.value,
        index=True,
    )
    legacy_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_notes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
