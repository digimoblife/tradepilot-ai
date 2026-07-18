from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime
from app.models.enums import AcceptanceStatus, AnalysisType

if TYPE_CHECKING:
    from app.models.analysis_job import AnalysisJob
    from app.models.session_event import SessionEvent
    from app.models.trade_session import TradeSession


class Analysis(Base):
    __tablename__ = "analyses"

    __table_args__ = (
        CheckConstraint(
            "supersedes_analysis_id IS NULL OR supersedes_analysis_id <> id",
            name="no_self_supersede",
        ),
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
        Index(
            "ix_analyses_session_type_created",
            "session_id",
            "analysis_type",
            text("created_at DESC"),
        ),
        Index(
            "ix_analyses_accepted",
            "session_id",
            text("created_at DESC"),
            postgresql_where=text("acceptance_status = 'ACCEPTED'"),
        ),
        Index(
            "ix_analyses_supersedes",
            "supersedes_analysis_id",
        ),
        Index(
            "ix_analyses_job",
            "analysis_job_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("trade_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    analysis_job_id: Mapped[uuid.UUID | None] = mapped_column(
        pg_uuid(),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    analysis_type: Mapped[AnalysisType] = mapped_column(
        SAEnum(AnalysisType, name="analysis_type_enum"),
        nullable=False,
    )
    acceptance_status: Mapped[AcceptanceStatus] = mapped_column(
        SAEnum(AcceptanceStatus, name="acceptance_status_enum"),
        default=AcceptanceStatus.PENDING,
        nullable=False,
    )
    prompt_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    supersedes_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        pg_uuid(),
        ForeignKey("analyses.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )

    trade_session: Mapped[TradeSession] = relationship(
        back_populates="analyses",
    )
    analysis_job: Mapped[AnalysisJob | None] = relationship(
        back_populates="analysis",
        uselist=False,
    )
    supersedes: Mapped[Analysis | None] = relationship(
        "Analysis",
        remote_side="Analysis.id",
        foreign_keys=[supersedes_analysis_id],
        back_populates="superseded_by",
        uselist=False,
    )
    superseded_by: Mapped[list[Analysis]] = relationship(
        "Analysis",
        remote_side=[supersedes_analysis_id],
        foreign_keys=[supersedes_analysis_id],
        back_populates="supersedes",
        uselist=True,
    )
    session_events: Mapped[list[SessionEvent]] = relationship(
        back_populates="related_analysis",
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("acceptance_status", AcceptanceStatus.PENDING)
        kwargs.setdefault("created_at", func.now())
        super().__init__(**kwargs)
