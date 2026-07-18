# ruff: noqa: E501
"""trade actions

Revision ID: 6730f9d6ee1d
Revises: 1025246d82f3
Create Date: 2026-07-18 06:36:38.086450

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6730f9d6ee1d"
down_revision: Union[str, Sequence[str], None] = "1025246d82f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_actions",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column(
            "action_type",
            sa.Enum(
                "POSITION_OPENED",
                "POSITION_CORRECTED",
                "STOP_LOSS_CONFIRMED",
                "STOP_LOSS_CHANGED",
                "TARGET_CONFIRMED",
                "TARGET_CHANGED",
                "PARTIAL_EXIT",
                "FULL_EXIT",
                "SESSION_CANCELLED",
                "SESSION_ARCHIVED",
                name="trade_action_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(20, 6), nullable=True),
        sa.Column("quantity", sa.Numeric(24, 6), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("related_analysis_id", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity >= 0",
            name=op.f("ck_trade_actions_quantity_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["trade_sessions.id"],
            name=op.f("fk_trade_actions_session_id_trade_sessions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trade_actions")),
    )
    op.create_index(
        op.f("ix_trade_actions_session_id"),
        "trade_actions",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_trade_actions_session_confirmed",
        "trade_actions",
        ["session_id", "confirmed_at"],
        unique=False,
    )
    op.create_index(
        "ix_trade_actions_session_type",
        "trade_actions",
        ["session_id", "action_type"],
        unique=False,
    )
    op.create_index(
        "ix_trade_actions_idempotency",
        "trade_actions",
        ["session_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_trade_actions_idempotency", table_name="trade_actions")
    op.drop_index("ix_trade_actions_session_type", table_name="trade_actions")
    op.drop_index("ix_trade_actions_session_confirmed", table_name="trade_actions")
    op.drop_index(op.f("ix_trade_actions_session_id"), table_name="trade_actions")
    op.drop_table("trade_actions")
    op.execute("DROP TYPE IF EXISTS trade_action_type_enum")
