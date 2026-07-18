"""context and events

Revision ID: 8e4d747e19db
Revises: fc58b8bbeab7
Create Date: 2026-07-18 07:51:03.309794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8e4d747e19db"
down_revision: Union[str, Sequence[str], None] = "fc58b8bbeab7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "context_summaries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("context_version", sa.Integer(), nullable=False),
        sa.Column("source_cutoff", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "quality",
            sa.Enum("HIGH", "MEDIUM", "LOW", "INCOMPLETE", "DEGRADED", name="context_quality_enum"),
            server_default=sa.text("'HIGH'::context_quality_enum"),
            nullable=False,
        ),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("context_version >= 1", name=op.f("ck_context_summaries_version")),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["trade_sessions.id"],
            name=op.f("fk_context_summaries_session_id_trade_sessions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_context_summaries")),
        sa.UniqueConstraint("session_id", "context_version", name=op.f("uq_context_summaries_session_version")),
    )
    op.create_index(
        "ix_context_summaries_session_created",
        "context_summaries",
        ["session_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_context_summaries_session_version",
        "context_summaries",
        ["session_id", sa.literal_column("context_version DESC")],
        unique=False,
    )
    op.create_table(
        "session_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "SESSION_CREATED",
                "EVIDENCE_UPLOADED",
                "ANALYSIS_REQUESTED",
                "ANALYSIS_ACCEPTED",
                "ANALYSIS_FAILED",
                "POSITION_OPENED",
                "STOP_LOSS_CHANGED",
                "TARGET_CHANGED",
                "PARTIAL_EXIT",
                "FULL_EXIT",
                "SESSION_ARCHIVED",
                "SESSION_RESTORED",
                "CONTEXT_REBUILT",
                "NOTE_ADDED",
                name="session_event_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("related_action_id", sa.UUID(), nullable=True),
        sa.Column("related_analysis_id", sa.UUID(), nullable=True),
        sa.Column("price", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=24, scale=6), nullable=True),
        sa.Column("compact_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity IS NULL OR quantity >= 0", name=op.f("ck_session_events_quantity")),
        sa.ForeignKeyConstraint(
            ["related_action_id"],
            ["trade_actions.id"],
            name=op.f("fk_session_events_related_action_id_trade_actions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["related_analysis_id"],
            ["analyses.id"],
            name=op.f("fk_session_events_related_analysis_id_analyses"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["trade_sessions.id"],
            name=op.f("fk_session_events_session_id_trade_sessions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_events")),
    )
    op.create_index("ix_session_events_chronological", "session_events", ["session_id", "occurred_at", "id"], unique=False)
    op.create_index("ix_session_events_related_action", "session_events", ["related_action_id"], unique=False)
    op.create_index("ix_session_events_related_analysis", "session_events", ["related_analysis_id"], unique=False)
    op.create_index("ix_session_events_type", "session_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_session_events_type", table_name="session_events")
    op.drop_index("ix_session_events_related_analysis", table_name="session_events")
    op.drop_index("ix_session_events_related_action", table_name="session_events")
    op.drop_index("ix_session_events_chronological", table_name="session_events")
    op.drop_table("session_events")
    op.drop_index("ix_context_summaries_session_version", table_name="context_summaries")
    op.drop_index("ix_context_summaries_session_created", table_name="context_summaries")
    op.drop_table("context_summaries")
    op.execute("DROP TYPE IF EXISTS context_quality_enum")
    op.execute("DROP TYPE IF EXISTS session_event_type_enum")
