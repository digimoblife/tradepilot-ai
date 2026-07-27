"""p1 lifecycle statuses

Revision ID: b7c9d1e2f3a4
Revises: 4a2b6c8d0e1f
Create Date: 2026-07-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b7c9d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "4a2b6c8d0e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for value in (
        "READY_FOR_INITIAL_ANALYSIS",
        "INITIAL_ANALYZED",
        "CLOSED",
        "CLOSED_SKIPPED",
    ):
        op.execute(f"ALTER TYPE session_status_enum ADD VALUE IF NOT EXISTS '{value}'")

    for value in ("USER_WAITED", "SESSION_SKIPPED"):
        op.execute(f"ALTER TYPE trade_action_type_enum ADD VALUE IF NOT EXISTS '{value}'")
        op.execute(f"ALTER TYPE session_event_type_enum ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without recreating dependent
    # columns and rewriting data. P1 is intentionally additive.
    pass
