from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import AccountStatus

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.trade_session import TradeSession


def normalize_email(email: str) -> str:
    return email.strip().lower()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(320), nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    account_status: Mapped[AccountStatus] = mapped_column(
        SAEnum(AccountStatus, name="account_status_enum"),
        default=AccountStatus.ACTIVE,
        nullable=False,
    )
    preferred_ui_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="id-ID"
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Jakarta"
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        utc_datetime(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    disabled_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)

    trade_sessions: Mapped[list[TradeSession]] = relationship(
        back_populates="user",
    )
    evidence_items: Mapped[list[Evidence]] = relationship(
        back_populates="owner",
    )

    def __init__(self, **kwargs: object) -> None:
        if "email" in kwargs:
            kwargs["email"] = normalize_email(str(kwargs["email"]))
        kwargs.setdefault("account_status", AccountStatus.ACTIVE)
        kwargs.setdefault("preferred_ui_language", "id-ID")
        kwargs.setdefault("timezone", "Asia/Jakarta")
        kwargs.setdefault("created_at", func.now())
        kwargs.setdefault("updated_at", func.now())
        super().__init__(**kwargs)
