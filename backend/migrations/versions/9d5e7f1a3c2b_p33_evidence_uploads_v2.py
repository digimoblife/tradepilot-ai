"""Add rebuild-owned evidence uploads table.

Revision ID: 9d5e7f1a3c2b
Revises: 8c4d2e6f1a3b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9d5e7f1a3c2b"
down_revision: str | None = "8c4d2e6f1a3b"
branch_labels: str | None = None
depends_on: str | None = None


_EVIDENCE_TYPES = ("ORDERBOOK", "CHART_3_MONTH", "CHART_6_MONTH")
_EVIDENCE_TYPE_ENUM = postgresql.ENUM(
    *_EVIDENCE_TYPES,
    name="evidence_upload_v2_type_enum",
)
_EVIDENCE_TYPE_ENUM_COLUMN = postgresql.ENUM(
    *_EVIDENCE_TYPES,
    name="evidence_upload_v2_type_enum",
    create_type=False,
)
_OBSERVATION_PERIOD_ENUM_COLUMN = postgresql.ENUM(
    "MORNING",
    "MIDDAY",
    "AFTERNOON",
    name="analysis_request_v2_observation_period_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _EVIDENCE_TYPE_ENUM.create(bind, checkfirst=True)

    op.create_table(
        "evidence_uploads_v2",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "analysis_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_requests_v2.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("evidence_type", _EVIDENCE_TYPE_ENUM_COLUMN, nullable=False),
        sa.Column("observation_period", _OBSERVATION_PERIOD_ENUM_COLUMN, nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("length(btrim(file_path)) > 0", name="file_path_not_blank"),
        sa.CheckConstraint(
            "length(btrim(original_filename)) > 0",
            name="original_filename_not_blank",
        ),
        sa.CheckConstraint("length(btrim(mime_type)) > 0", name="mime_type_not_blank"),
        sa.CheckConstraint("size_bytes > 0", name="size_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_uploads_v2_session_id", "evidence_uploads_v2", ["session_id"])
    op.create_index(
        "ix_evidence_uploads_v2_analysis_request_id",
        "evidence_uploads_v2",
        ["analysis_request_id"],
    )
    op.create_index(
        "ix_evidence_uploads_v2_evidence_type",
        "evidence_uploads_v2",
        ["evidence_type"],
    )
    op.create_index("ix_evidence_uploads_v2_uploaded_at", "evidence_uploads_v2", ["uploaded_at"])


def downgrade() -> None:
    op.drop_index("ix_evidence_uploads_v2_uploaded_at", table_name="evidence_uploads_v2")
    op.drop_index("ix_evidence_uploads_v2_evidence_type", table_name="evidence_uploads_v2")
    op.drop_index(
        "ix_evidence_uploads_v2_analysis_request_id",
        table_name="evidence_uploads_v2",
    )
    op.drop_index("ix_evidence_uploads_v2_session_id", table_name="evidence_uploads_v2")
    op.drop_table("evidence_uploads_v2")
    _EVIDENCE_TYPE_ENUM.drop(op.get_bind(), checkfirst=True)
