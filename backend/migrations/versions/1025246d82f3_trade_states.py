# ruff: noqa: E501
"""trade states

Revision ID: 1025246d82f3
Revises: 5dac6cef5c21
Create Date: 2026-07-18 03:52:24.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "1025246d82f3"
down_revision: Union[str, Sequence[str], None] = "5dac6cef5c21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_states",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column(
            "position_status",
            sa.Enum(
                "NOT_OPENED",
                "OPEN",
                "PARTIALLY_CLOSED",
                "CLOSED",
                name="position_status_enum",
            ),
            server_default=sa.text("'NOT_OPENED'::position_status_enum"),
            nullable=False,
        ),
        sa.Column(
            "thesis_status",
            sa.Enum(
                "STRENGTHENING",
                "INTACT",
                "INTACT_BUT_WEAKENING",
                "UNDER_REVIEW",
                "INVALIDATED",
                name="thesis_status_enum",
            ),
            server_default=sa.text("'INTACT'::thesis_status_enum"),
            nullable=False,
        ),
        sa.Column("entry_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("entry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("original_quantity", sa.Numeric(24, 6), nullable=True),
        sa.Column("remaining_quantity", sa.Numeric(24, 6), nullable=True),
        sa.Column("active_stop_loss", sa.Numeric(20, 6), nullable=True),
        sa.Column("active_target", sa.Numeric(20, 6), nullable=True),
        sa.Column("average_exit_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(24, 6), nullable=True),
        sa.Column("realized_return", sa.Numeric(12, 6), nullable=True),
        sa.Column(
            "last_confirmed_action_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "state_version",
            sa.BigInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["trade_sessions.id"],
            name=op.f("fk_trade_states_session_id_trade_sessions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("session_id", name=op.f("pk_trade_states")),
        sa.CheckConstraint(
            "original_quantity IS NULL OR original_quantity >= 0",
            name=op.f("ck_trade_states_original_quantity_non_negative"),
        ),
        sa.CheckConstraint(
            "remaining_quantity IS NULL OR remaining_quantity >= 0",
            name=op.f("ck_trade_states_remaining_quantity_non_negative"),
        ),
        sa.CheckConstraint(
            "original_quantity IS NULL OR remaining_quantity IS NULL "
            "OR remaining_quantity <= original_quantity",
            name=op.f("ck_trade_states_remaining_not_above_original"),
        ),
        sa.CheckConstraint(
            "state_version >= 1",
            name=op.f("ck_trade_states_state_version_min"),
        ),
    )
    op.create_index(
        op.f("ix_trade_states_position_status"),
        "trade_states",
        ["position_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_trade_states_entry_at"),
        "trade_states",
        [sa.text("entry_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_trade_states_session_status",
        "trade_states",
        ["position_status", "session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trade_states_session_status", table_name="trade_states")
    op.drop_index(op.f("ix_trade_states_entry_at"), table_name="trade_states")
    op.drop_index(op.f("ix_trade_states_position_status"), table_name="trade_states")
    op.drop_table("trade_states")
    op.execute("DROP TYPE IF EXISTS position_status_enum")
    op.execute("DROP TYPE IF EXISTS thesis_status_enum")
