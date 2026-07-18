from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import ProviderResponseStatus

if TYPE_CHECKING:
    from app.models.provider_request import ProviderRequest
    from app.models.validation_attempt import ValidationAttempt


class ProviderResponse(Base):
    __tablename__ = "provider_responses"

    __table_args__ = (
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency"),
        CheckConstraint("input_tokens IS NULL OR input_tokens >= 0", name="input_tokens"),
        CheckConstraint("output_tokens IS NULL OR output_tokens >= 0", name="output_tokens"),
        CheckConstraint("total_tokens IS NULL OR total_tokens >= 0", name="total_tokens"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    provider_request_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("provider_requests.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[ProviderResponseStatus] = mapped_column(
        SAEnum(ProviderResponseStatus, name="provider_response_status_enum"),
        default=ProviderResponseStatus.PROCESSING,
        nullable=False,
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    provider_response_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    usage_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    provider_request: Mapped[ProviderRequest] = relationship(
        back_populates="responses",
    )
    validation_attempts: Mapped[list[ValidationAttempt]] = relationship(
        back_populates="provider_response",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("status", ProviderResponseStatus.PROCESSING)
        kwargs.setdefault("received_at", func.now())
        kwargs.setdefault("created_at", func.now())
        super().__init__(**kwargs)
