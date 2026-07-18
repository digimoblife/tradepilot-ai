# ruff: noqa: E501
"""evidence

Revision ID: 9d219c5a02e1
Revises: 6730f9d6ee1d
Create Date: 2026-07-18 06:50:57.570975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9d219c5a02e1"
down_revision: Union[str, Sequence[str], None] = "6730f9d6ee1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "evidence_type",
            sa.Enum("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH",
                    "CHART_DAILY", "CHART_INTRADAY", "BROKER_SUMMARY", "FOREIGN_FLOW",
                    "NEWS_SCREENSHOT", "CUSTOM_IMAGE", "USER_NOTE", "MARKET_DATA_SNAPSHOT",
                    name="evidence_type_enum"),
            nullable=False,
        ),
        sa.Column(
            "evidence_status",
            sa.Enum("PENDING", "AVAILABLE", "PROCESSING", "UNREADABLE",
                    "SUPERSEDED", "EXCLUDED", "DUPLICATE", "FAILED", "DELETED",
                    name="evidence_status_enum"),
            server_default=sa.text("'PENDING'::evidence_status_enum"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("storage_object_key", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("market_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column(
            "extraction_status",
            sa.Enum("NOT_REQUESTED", "PENDING", "PROCESSING",
                    "COMPLETED", "PARTIAL", "FAILED",
                    name="extraction_status_enum"),
            server_default=sa.text("'NOT_REQUESTED'::extraction_status_enum"),
            nullable=False,
        ),
        sa.Column("extraction_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(7, 4), nullable=True),
        sa.Column("supersedes_evidence_id", sa.UUID(), nullable=True),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("excluded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name=op.f("ck_evidence_file_size_non_negative"),
        ),
        sa.CheckConstraint(
            "extraction_confidence IS NULL OR (extraction_confidence >= 0 AND extraction_confidence <= 100)",
            name=op.f("ck_evidence_extraction_confidence_range"),
        ),
        sa.CheckConstraint(
            "evidence_status <> 'EXCLUDED' OR (exclusion_reason IS NOT NULL AND excluded_at IS NOT NULL)",
            name=op.f("ck_evidence_excluded_state"),
        ),
        sa.CheckConstraint(
            "checksum_sha256 IS NULL OR checksum_sha256 ~ '^[0-9a-fA-F]{64}$'",
            name=op.f("ck_evidence_checksum_format"),
        ),
        sa.CheckConstraint(
            "supersedes_evidence_id IS NULL OR supersedes_evidence_id <> id",
            name=op.f("ck_evidence_no_self_replacement"),
        ),
        sa.CheckConstraint(
            "storage_object_key IS NULL OR "
            "(storage_object_key <> '' "
            "AND LEFT(storage_object_key, 1) <> '/' "
            "AND storage_object_key NOT LIKE '%..%')",
            name=op.f("ck_evidence_safe_storage_key"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["trade_sessions.id"],
            name=op.f("fk_evidence_session_id_trade_sessions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"],
            name=op.f("fk_evidence_owner_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence")),
    )
    op.create_foreign_key(
        op.f("fk_evidence_supersedes_evidence_id_evidence"),
        "evidence", "evidence",
        ["supersedes_evidence_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_evidence_session_id"), "evidence", ["session_id"], unique=False)
    op.create_index(
        op.f("ix_evidence_session_uploaded"),
        "evidence", ["session_id", sa.text("uploaded_at DESC")], unique=False,
    )
    op.create_index(
        op.f("ix_evidence_session_type_status"),
        "evidence", ["session_id", "evidence_type", "evidence_status"], unique=False,
    )
    op.create_index(
        op.f("ix_evidence_session_market_time"),
        "evidence", ["session_id", sa.text("market_timestamp DESC")], unique=False,
    )
    op.create_index(
        op.f("ix_evidence_owner_checksum"),
        "evidence", ["owner_id", "checksum_sha256"], unique=False,
        postgresql_where=sa.text("checksum_sha256 IS NOT NULL"),
    )
    op.create_index(
        "ix_evidence_active_initial",
        "evidence", ["session_id", "evidence_type"], unique=False,
        postgresql_where=sa.text(
            "evidence_status = 'AVAILABLE' AND deleted_at IS NULL "
            "AND evidence_type IN ('ORDERBOOK_SCREENSHOT', 'CHART_THREE_MONTH', 'CHART_SIX_MONTH')"
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_active_initial", table_name="evidence")
    op.drop_index(op.f("ix_evidence_owner_checksum"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_session_market_time"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_session_type_status"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_session_uploaded"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_session_id"), table_name="evidence")
    op.drop_constraint(
        op.f("fk_evidence_supersedes_evidence_id_evidence"),
        "evidence", type_="foreignkey",
    )
    op.drop_table("evidence")
    op.execute("DROP TYPE IF EXISTS evidence_type_enum")
    op.execute("DROP TYPE IF EXISTS evidence_status_enum")
    op.execute("DROP TYPE IF EXISTS extraction_status_enum")
