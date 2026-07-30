"""Add rebuild-owned trade closures table.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "trade_closures_v2",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "position_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("positions_v2.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("close_price", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("close_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_reason", sa.String(length=64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "realized_profit_loss",
            sa.Numeric(precision=24, scale=6),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("close_price > 0", name="close_price_positive"),
        sa.CheckConstraint(
            "length(btrim(close_reason)) > 0",
            name="close_reason_not_blank",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position_id", name="uq_trade_closures_v2_position_id"),
    )
    op.create_index(
        "ix_trade_closures_v2_session_id",
        "trade_closures_v2",
        ["session_id"],
    )
    op.create_index(
        "ix_trade_closures_v2_close_at",
        "trade_closures_v2",
        ["close_at"],
    )
    op.create_index(
        "ix_trade_closures_v2_created_at",
        "trade_closures_v2",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_trade_closures_v2_created_at", table_name="trade_closures_v2")
    op.drop_index("ix_trade_closures_v2_close_at", table_name="trade_closures_v2")
    op.drop_index("ix_trade_closures_v2_session_id", table_name="trade_closures_v2")
    op.drop_table("trade_closures_v2")
