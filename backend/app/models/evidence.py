# ruff: noqa: E501
from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import percentage_numeric, pg_uuid, utc_datetime
from app.models.enums import EvidenceStatus, EvidenceType, ExtractionStatus

if TYPE_CHECKING:
    from app.models.trade_session import TradeSession
    from app.models.user import User


def normalize_storage_object_key(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Storage object key must not be empty")
    if "\x00" in stripped:
        raise ValueError("Storage object key must not contain null characters")

    if stripped.startswith("./") or stripped.startswith(".\\"):
        raise ValueError(
            f"Storage object key must not contain current-directory segment: {stripped!r}"
        )

    if stripped.startswith("//") or stripped.startswith("\\\\"):
        raise ValueError(f"Storage object key must not be a UNC path: {stripped!r}")

    p = PurePosixPath(stripped)
    if p.is_absolute():
        raise ValueError(f"Storage object key must be relative: {stripped!r}")
    if ".." in p.parts:
        raise ValueError(f"Storage object key must not contain traversal segments: {stripped!r}")
    if "." in p.parts:
        raise ValueError(
            f"Storage object key must not contain current-directory segment: {stripped!r}"
        )
    if re.match(r"^[A-Za-z]:[/\\]", stripped):
        raise ValueError(f"Storage object key must not contain Windows drive prefix: {stripped!r}")
    return stripped


class Evidence(Base):
    __tablename__ = "evidence"

    __table_args__ = (
        CheckConstraint(
            "supersedes_evidence_id IS NULL OR supersedes_evidence_id <> id",
            name="no_self_replacement",
        ),
        CheckConstraint(
            "storage_object_key IS NULL OR "
            "(storage_object_key <> '' "
            "AND LEFT(storage_object_key, 1) <> '/' "
            "AND storage_object_key NOT LIKE '%..%')",
            name="safe_storage_key",
        ),
        Index(
            "ix_evidence_session_uploaded",
            "session_id",
            text("uploaded_at DESC"),
        ),
        Index(
            "ix_evidence_session_type_status",
            "session_id",
            "evidence_type",
            "evidence_status",
        ),
        Index(
            "ix_evidence_owner_checksum",
            "owner_id",
            "checksum_sha256",
            postgresql_where=text("checksum_sha256 IS NOT NULL"),
        ),
        Index(
            "ix_evidence_session_market_time",
            "session_id",
            text("market_timestamp DESC"),
        ),
        Index(
            "ix_evidence_active_initial",
            "session_id",
            "evidence_type",
            postgresql_where=text(
                "evidence_status = 'AVAILABLE' AND deleted_at IS NULL "
                "AND evidence_type IN ('ORDERBOOK_SCREENSHOT', 'CHART_THREE_MONTH', 'CHART_SIX_MONTH')"
            ),
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
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        SAEnum(EvidenceType, name="evidence_type_enum"),
        nullable=False,
    )
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        SAEnum(EvidenceStatus, name="evidence_status_enum"),
        default=EvidenceStatus.PENDING,
        nullable=False,
    )
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_timestamp: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        SAEnum(ExtractionStatus, name="extraction_status_enum"),
        default=ExtractionStatus.NOT_REQUESTED,
        nullable=False,
    )
    extraction_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(
        percentage_numeric(), nullable=True
    )
    supersedes_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        pg_uuid(),
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        nullable=True,
    )
    exclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    excluded_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)

    trade_session: Mapped[TradeSession] = relationship(
        back_populates="evidence_items",
    )
    owner: Mapped[User] = relationship(
        back_populates="evidence_items",
    )
    supersedes: Mapped[Evidence | None] = relationship(
        "Evidence",
        remote_side="Evidence.id",
        foreign_keys=[supersedes_evidence_id],
        back_populates="superseded_by_items",
        uselist=False,
    )
    superseded_by_items: Mapped[list[Evidence]] = relationship(
        "Evidence",
        remote_side=[supersedes_evidence_id],
        foreign_keys=[supersedes_evidence_id],
        back_populates="supersedes",
        uselist=True,
    )

    def __init__(self, **kwargs: object) -> None:
        if "storage_object_key" in kwargs and kwargs["storage_object_key"] is not None:
            kwargs["storage_object_key"] = normalize_storage_object_key(
                str(kwargs["storage_object_key"])
            )
        kwargs.setdefault("evidence_status", EvidenceStatus.PENDING)
        kwargs.setdefault("extraction_status", ExtractionStatus.NOT_REQUESTED)
        kwargs.setdefault("uploaded_at", func.now())
        kwargs.setdefault("created_at", func.now())
        kwargs.setdefault("updated_at", func.now())
        super().__init__(**kwargs)
