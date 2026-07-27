"""p2 evidence batches

Revision ID: c8d9e0f1a2b3
Revises: b7c9d1e2f3a4
Create Date: 2026-07-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c9d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE evidence_batch_status_enum AS ENUM "
        "('DRAFT', 'READY', 'PROCESSING', 'FROZEN', 'FAILED')"
    )

    op.create_table(
        "evidence_batches",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "analysis_type",
            postgresql.ENUM(
                "INITIAL_ANALYSIS",
                "WATCHING_UPDATE",
                "OPEN_POSITION_UPDATE",
                "PARTIAL_EXIT_REVIEW",
                "CLOSING_ANALYSIS",
                name="analysis_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DRAFT",
                "READY",
                "PROCESSING",
                "FROZEN",
                "FAILED",
                name="evidence_batch_status_enum",
                create_type=False,
            ),
            server_default=sa.text("'DRAFT'::evidence_batch_status_enum"),
            nullable=False,
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("sequence_number > 0", name=op.f("ck_evidence_batches_evidence_batch_sequence_positive")),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_evidence_batches_owner_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["trade_sessions.id"],
            name=op.f("fk_evidence_batches_session_id_trade_sessions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_batches")),
        sa.UniqueConstraint(
            "session_id",
            "analysis_type",
            "sequence_number",
            name="uq_evidence_batches_session_analysis_sequence",
        ),
    )
    op.create_index(
        "ix_evidence_batches_session_created",
        "evidence_batches",
        ["session_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_batches_session_status",
        "evidence_batches",
        ["session_id", "status"],
        unique=False,
    )
    op.create_index(op.f("ix_evidence_batches_owner_id"), "evidence_batches", ["owner_id"])
    op.create_index(op.f("ix_evidence_batches_session_id"), "evidence_batches", ["session_id"])

    op.add_column("evidence", sa.Column("evidence_batch_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_evidence_evidence_batch_id_evidence_batches"),
        "evidence",
        "evidence_batches",
        ["evidence_batch_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_evidence_evidence_batch_id"), "evidence", ["evidence_batch_id"])
    op.create_index(
        "ix_evidence_batch_type_status",
        "evidence",
        ["evidence_batch_id", "evidence_type", "evidence_status"],
        unique=False,
    )

    op.add_column("analysis_jobs", sa.Column("evidence_batch_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_analysis_jobs_evidence_batch_id_evidence_batches"),
        "analysis_jobs",
        "evidence_batches",
        ["evidence_batch_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_analysis_jobs_evidence_batch", "analysis_jobs", ["evidence_batch_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_evidence_batch", table_name="analysis_jobs")
    op.drop_constraint(
        op.f("fk_analysis_jobs_evidence_batch_id_evidence_batches"),
        "analysis_jobs",
        type_="foreignkey",
    )
    op.drop_column("analysis_jobs", "evidence_batch_id")

    op.drop_index("ix_evidence_batch_type_status", table_name="evidence")
    op.drop_index(op.f("ix_evidence_evidence_batch_id"), table_name="evidence")
    op.drop_constraint(
        op.f("fk_evidence_evidence_batch_id_evidence_batches"),
        "evidence",
        type_="foreignkey",
    )
    op.drop_column("evidence", "evidence_batch_id")

    op.drop_index(op.f("ix_evidence_batches_session_id"), table_name="evidence_batches")
    op.drop_index(op.f("ix_evidence_batches_owner_id"), table_name="evidence_batches")
    op.drop_index("ix_evidence_batches_session_status", table_name="evidence_batches")
    op.drop_index("ix_evidence_batches_session_created", table_name="evidence_batches")
    op.drop_table("evidence_batches")
    op.execute("DROP TYPE IF EXISTS evidence_batch_status_enum")
