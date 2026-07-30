"""Add rebuild-owned session decisions table.

Revision ID: a7b8c9d0e1f2
Revises: 9d5e7f1a3c2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "9d5e7f1a3c2b"
branch_labels: str | None = None
depends_on: str | None = None


_DECISIONS = ("BUY", "WAIT", "SKIP")
_REASONS = (
    "RISK_TOO_HIGH",
    "SETUP_NOT_ATTRACTIVE",
    "ORDERBOOK_WEAK",
    "MARKET_CONDITION_UNFAVORABLE",
    "WAITING_TOO_LONG",
    "USER_DECISION",
    "OTHER",
)

_DECISION_ENUM = postgresql.ENUM(
    *_DECISIONS,
    name="session_decision_v2_decision_enum",
)
_DECISION_ENUM_COLUMN = postgresql.ENUM(
    *_DECISIONS,
    name="session_decision_v2_decision_enum",
    create_type=False,
)
_REASON_ENUM = postgresql.ENUM(
    *_REASONS,
    name="session_decision_v2_reason_enum",
)
_REASON_ENUM_COLUMN = postgresql.ENUM(
    *_REASONS,
    name="session_decision_v2_reason_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _DECISION_ENUM.create(bind, checkfirst=True)
    _REASON_ENUM.create(bind, checkfirst=True)

    op.create_table(
        "session_decisions_v2",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trade_sessions_v2.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision", _DECISION_ENUM_COLUMN, nullable=False),
        sa.Column("reason", _REASON_ENUM_COLUMN, nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_session_decisions_v2_session_id", "session_decisions_v2", ["session_id"])
    op.create_index("ix_session_decisions_v2_decision", "session_decisions_v2", ["decision"])
    op.create_index("ix_session_decisions_v2_created_at", "session_decisions_v2", ["created_at"])
    op.create_index(
        "uq_session_decisions_v2_one_buy_per_session",
        "session_decisions_v2",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("decision = 'BUY'::session_decision_v2_decision_enum"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_session_decisions_v2_one_buy_per_session",
        table_name="session_decisions_v2",
        postgresql_where=sa.text("decision = 'BUY'::session_decision_v2_decision_enum"),
    )
    op.drop_index("ix_session_decisions_v2_created_at", table_name="session_decisions_v2")
    op.drop_index("ix_session_decisions_v2_decision", table_name="session_decisions_v2")
    op.drop_index("ix_session_decisions_v2_session_id", table_name="session_decisions_v2")
    op.drop_table("session_decisions_v2")
    _REASON_ENUM.drop(op.get_bind(), checkfirst=True)
    _DECISION_ENUM.drop(op.get_bind(), checkfirst=True)
