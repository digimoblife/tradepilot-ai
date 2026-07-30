"""Add rebuild-owned analysis requests table.

Revision ID: 8c4d2e6f1a3b
Revises: 7f3a9c2d1b4e
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8c4d2e6f1a3b"
down_revision: str | None = "7f3a9c2d1b4e"
branch_labels: str | None = None
depends_on: str | None = None


_ANALYSIS_TYPES = ("INITIAL_ANALYSIS", "WAIT_UPDATE", "POSITION_UPDATE")
_OBSERVATION_PERIODS = ("MORNING", "MIDDAY", "AFTERNOON")
_STATUSES = ("PENDING", "PROCESSING", "COMPLETED", "FAILED")

_ANALYSIS_TYPE_ENUM = postgresql.ENUM(
    *_ANALYSIS_TYPES,
    name="analysis_request_v2_type_enum",
)
_ANALYSIS_TYPE_ENUM_COLUMN = postgresql.ENUM(
    *_ANALYSIS_TYPES,
    name="analysis_request_v2_type_enum",
    create_type=False,
)
_OBSERVATION_PERIOD_ENUM = postgresql.ENUM(
    *_OBSERVATION_PERIODS,
    name="analysis_request_v2_observation_period_enum",
)
_OBSERVATION_PERIOD_ENUM_COLUMN = postgresql.ENUM(
    *_OBSERVATION_PERIODS,
    name="analysis_request_v2_observation_period_enum",
    create_type=False,
)
_STATUS_ENUM = postgresql.ENUM(
    *_STATUSES,
    name="analysis_request_v2_status_enum",
)
_STATUS_ENUM_COLUMN = postgresql.ENUM(
    *_STATUSES,
    name="analysis_request_v2_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _ANALYSIS_TYPE_ENUM.create(bind, checkfirst=True)
    _OBSERVATION_PERIOD_ENUM.create(bind, checkfirst=True)
    _STATUS_ENUM.create(bind, checkfirst=True)

    op.create_table(
        "analysis_requests_v2",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("analysis_type", _ANALYSIS_TYPE_ENUM_COLUMN, nullable=False),
        sa.Column("observation_period", _OBSERVATION_PERIOD_ENUM_COLUMN, nullable=True),
        sa.Column("current_price", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("observation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            _STATUS_ENUM_COLUMN,
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("processed_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("current_price IS NULL OR current_price > 0", name="price_positive"),
        sa.CheckConstraint("provider = 'gemini'", name="provider_gemini_only"),
        sa.CheckConstraint(
            "analysis_type = 'INITIAL_ANALYSIS' OR (current_price IS NOT NULL "
            "AND observation_period IS NOT NULL AND observation_at IS NOT NULL)",
            name="observation_fields_required",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_requests_v2_session_id", "analysis_requests_v2", ["session_id"])
    op.create_index("ix_analysis_requests_v2_status", "analysis_requests_v2", ["status"])
    op.create_index(
        "ix_analysis_requests_v2_analysis_type",
        "analysis_requests_v2",
        ["analysis_type"],
    )
    op.create_index("ix_analysis_requests_v2_created_at", "analysis_requests_v2", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_analysis_requests_v2_created_at", table_name="analysis_requests_v2")
    op.drop_index("ix_analysis_requests_v2_analysis_type", table_name="analysis_requests_v2")
    op.drop_index("ix_analysis_requests_v2_status", table_name="analysis_requests_v2")
    op.drop_index("ix_analysis_requests_v2_session_id", table_name="analysis_requests_v2")
    op.drop_table("analysis_requests_v2")
    _STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
    _OBSERVATION_PERIOD_ENUM.drop(op.get_bind(), checkfirst=True)
    _ANALYSIS_TYPE_ENUM.drop(op.get_bind(), checkfirst=True)
