from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime


class SessionDecisionV2Decision(str, enum.Enum):
    BUY = "BUY"
    WAIT = "WAIT"
    SKIP = "SKIP"


class SessionDecisionV2Reason(str, enum.Enum):
    RISK_TOO_HIGH = "RISK_TOO_HIGH"
    SETUP_NOT_ATTRACTIVE = "SETUP_NOT_ATTRACTIVE"
    ORDERBOOK_WEAK = "ORDERBOOK_WEAK"
    MARKET_CONDITION_UNFAVORABLE = "MARKET_CONDITION_UNFAVORABLE"
    WAITING_TOO_LONG = "WAITING_TOO_LONG"
    USER_DECISION = "USER_DECISION"
    OTHER = "OTHER"


class SessionDecisionV2(Base):
    __tablename__ = "session_decisions_v2"

    __table_args__ = (
        Index("ix_session_decisions_v2_session_id", "session_id"),
        Index("ix_session_decisions_v2_decision", "decision"),
        Index("ix_session_decisions_v2_created_at", "created_at"),
        Index(
            "uq_session_decisions_v2_one_buy_per_session",
            "session_id",
            unique=True,
            postgresql_where=text("decision = 'BUY'::session_decision_v2_decision_enum"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[SessionDecisionV2Decision] = mapped_column(
        SAEnum(
            SessionDecisionV2Decision,
            name="session_decision_v2_decision_enum",
            native_enum=True,
        ),
        nullable=False,
    )
    reason: Mapped[SessionDecisionV2Reason | None] = mapped_column(
        SAEnum(
            SessionDecisionV2Reason,
            name="session_decision_v2_reason_enum",
            native_enum=True,
        ),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
