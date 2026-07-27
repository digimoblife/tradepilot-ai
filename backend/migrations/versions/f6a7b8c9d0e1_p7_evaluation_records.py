"""P7: Add evaluation_records table.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-27

Adds evaluation_records table to capture structured predictions, user decisions,
and trade outcomes without storing raw provider payloads or images.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: str = "e5f6a7b8c9d0"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trade_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("prompt_name", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(20), nullable=True),
        sa.Column("schema_name", sa.String(100), nullable=True),
        sa.Column("schema_version", sa.String(20), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("model", sa.String(50), nullable=True),
        sa.Column("prediction_data", sa.JSON(), nullable=False, server_default="{}" ),
        sa.Column("user_decision_data", sa.JSON(), nullable=False, server_default="{}" ),
        sa.Column("outcome_data", sa.JSON(), nullable=False, server_default="{}" ),
        sa.Column("completeness_status", sa.String(30), nullable=False, server_default="PARTIAL"),
        sa.Column("legacy_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validation_warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_notes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("ix_eval_records_owner_id", "evaluation_records", ["owner_id"])
    op.create_index("ix_eval_records_session_id", "evaluation_records", ["session_id"])
    op.create_index("ix_eval_records_ticker", "evaluation_records", ["ticker"])
    op.create_index("ix_eval_records_analysis_type", "evaluation_records", ["analysis_type"])
    op.create_index("ix_eval_records_completeness", "evaluation_records", ["completeness_status"])

    # Unique index for session + analysis idempotency
    op.create_index(
        "uq_eval_records_session_analysis",
        "evaluation_records",
        ["session_id", "source_analysis_id"],
        unique=True,
        postgresql_where=sa.text("source_analysis_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_eval_records_session_analysis", table_name="evaluation_records")
    op.drop_index("ix_eval_records_completeness", table_name="evaluation_records")
    op.drop_index("ix_eval_records_analysis_type", table_name="evaluation_records")
    op.drop_index("ix_eval_records_ticker", table_name="evaluation_records")
    op.drop_index("ix_eval_records_session_id", table_name="evaluation_records")
    op.drop_index("ix_eval_records_owner_id", table_name="evaluation_records")
    op.drop_table("evaluation_records")
