"""Add rebuild-owned positions table.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | None = None
depends_on: str | None = None


_STATUSES = ("OPEN", "CLOSED")
_STATUS_ENUM = postgresql.ENUM(
    *_STATUSES,
    name="position_v2_status_enum",
)
_STATUS_ENUM_COLUMN = postgresql.ENUM(
    *_STATUSES,
    name="position_v2_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _STATUS_ENUM.create(bind, checkfirst=True)

    op.create_table(
        "positions_v2",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("entry_price", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("entry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column("stop_loss", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("target_price", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            _STATUS_ENUM_COLUMN,
            nullable=False,
            server_default=sa.text("'OPEN'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("entry_price > 0", name="entry_price_positive"),
        sa.CheckConstraint("quantity > 0", name="quantity_positive"),
        sa.CheckConstraint("stop_loss > 0", name="stop_loss_positive"),
        sa.CheckConstraint("target_price > 0", name="target_price_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_positions_v2_session_id"),
    )
    op.create_index("ix_positions_v2_status", "positions_v2", ["status"])
    op.create_index("ix_positions_v2_created_at", "positions_v2", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_positions_v2_created_at", table_name="positions_v2")
    op.drop_index("ix_positions_v2_status", table_name="positions_v2")
    op.drop_table("positions_v2")
    _STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
