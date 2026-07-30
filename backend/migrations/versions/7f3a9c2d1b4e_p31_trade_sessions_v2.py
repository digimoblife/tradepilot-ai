"""Add rebuild-owned trade sessions table.

Revision ID: 7f3a9c2d1b4e
Revises: f6a7b8c9d0e1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7f3a9c2d1b4e"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | None = "rebuild"
depends_on: str | None = None


_STATUS_VALUES = (
    "DRAFT",
    "ANALYZING",
    "ANALYZED",
    "WAITING",
    "OPEN_POSITION",
    "CLOSED",
    "CLOSED_SKIPPED",
)
_STATUS_ENUM = postgresql.ENUM(
    *_STATUS_VALUES,
    name="trade_session_v2_status_enum",
)
_STATUS_ENUM_COLUMN = postgresql.ENUM(
    *_STATUS_VALUES,
    name="trade_session_v2_status_enum",
    create_type=False,
)


def upgrade() -> None:
    _STATUS_ENUM.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "trade_sessions_v2",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            _STATUS_ENUM_COLUMN,
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(btrim(ticker)) > 0", name="ticker_not_blank"),
        sa.CheckConstraint("length(btrim(company_name)) > 0", name="company_name_not_blank"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trade_sessions_v2_user_id", "trade_sessions_v2", ["user_id"])
    op.create_index("ix_trade_sessions_v2_status", "trade_sessions_v2", ["status"])
    op.create_index("ix_trade_sessions_v2_created_at", "trade_sessions_v2", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_trade_sessions_v2_created_at", table_name="trade_sessions_v2")
    op.drop_index("ix_trade_sessions_v2_status", table_name="trade_sessions_v2")
    op.drop_index("ix_trade_sessions_v2_user_id", table_name="trade_sessions_v2")
    op.drop_table("trade_sessions_v2")
    _STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
