# ruff: noqa: E501

"""users trade sessions

Revision ID: 5dac6cef5c21
Revises: 03f81601e437
Create Date: 2026-07-18 03:20:22.029637

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5dac6cef5c21"
down_revision: Union[str, Sequence[str], None] = "03f81601e437"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("username", sa.String(320), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "account_status",
            sa.Enum("ACTIVE", "LOCKED", "DISABLED", name="account_status_enum"),
            server_default=sa.text("'ACTIVE'::account_status_enum"),
            nullable=False,
        ),
        sa.Column(
            "preferred_ui_language",
            sa.String(10),
            server_default=sa.text("'id-ID'"),
            nullable=False,
        ),
        sa.Column(
            "timezone",
            sa.String(64),
            server_default=sa.text("'Asia/Jakarta'"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "trade_sessions",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column(
            "market",
            sa.Enum("IDX", "NASDAQ", "NYSE", "AMEX", "OTHER", name="market_enum"),
            server_default=sa.text("'IDX'::market_enum"),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.Enum("IDR", "USD", "OTHER", name="currency_enum"),
            server_default=sa.text("'IDR'::currency_enum"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("initial_note", sa.Text(), nullable=True),
        sa.Column(
            "lifecycle_status",
            sa.Enum(
                "DRAFT",
                "READY_FOR_ANALYSIS",
                "ANALYZING",
                "WATCHING",
                "OPEN_POSITION",
                "PARTIALLY_CLOSED",
                "CLOSED_TAKE_PROFIT",
                "CLOSED_STOP_LOSS",
                "CLOSED_MANUAL",
                "CANCELLED",
                "ARCHIVED",
                name="session_status_enum",
            ),
            server_default=sa.text("'DRAFT'::session_status_enum"),
            nullable=False,
        ),
        sa.Column(
            "stable_status",
            sa.Enum(
                "DRAFT",
                "READY_FOR_ANALYSIS",
                "ANALYZING",
                "WATCHING",
                "OPEN_POSITION",
                "PARTIALLY_CLOSED",
                "CLOSED_TAKE_PROFIT",
                "CLOSED_STOP_LOSS",
                "CLOSED_MANUAL",
                "CANCELLED",
                "ARCHIVED",
                name="session_status_enum",
            ),
            server_default=sa.text("'DRAFT'::session_status_enum"),
            nullable=False,
        ),
        sa.Column(
            "pre_archive_status",
            sa.Enum(
                "DRAFT",
                "READY_FOR_ANALYSIS",
                "ANALYZING",
                "WATCHING",
                "OPEN_POSITION",
                "PARTIALLY_CLOSED",
                "CLOSED_TAKE_PROFIT",
                "CLOSED_STOP_LOSS",
                "CLOSED_MANUAL",
                "CANCELLED",
                "ARCHIVED",
                name="session_status_enum",
            ),
            nullable=True,
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "version", sa.BigInteger(), server_default=sa.text("1"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_trade_sessions_owner_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trade_sessions")),
    )
    op.create_index(
        op.f("ix_trade_sessions_owner_id"), "trade_sessions", ["owner_id"], unique=False
    )
    op.create_index(
        op.f("ix_trade_sessions_ticker"), "trade_sessions", ["ticker"], unique=False
    )
    op.create_index(
        op.f("ix_trade_sessions_owner_lifecycle"),
        "trade_sessions",
        ["owner_id", "lifecycle_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_trade_sessions_owner_updated"),
        "trade_sessions",
        ["owner_id", sa.text("updated_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_trade_sessions_owner_updated"), table_name="trade_sessions")
    op.drop_index(
        op.f("ix_trade_sessions_owner_lifecycle"), table_name="trade_sessions"
    )
    op.drop_index(op.f("ix_trade_sessions_ticker"), table_name="trade_sessions")
    op.drop_index(op.f("ix_trade_sessions_owner_id"), table_name="trade_sessions")
    op.drop_table("trade_sessions")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS session_status_enum")
    op.execute("DROP TYPE IF EXISTS market_enum")
    op.execute("DROP TYPE IF EXISTS currency_enum")
    op.execute("DROP TYPE IF EXISTS account_status_enum")
