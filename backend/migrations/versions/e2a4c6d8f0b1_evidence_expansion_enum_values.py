"""Add Foreign Flow and Broker Flow rebuild evidence types.

Revision ID: e2a4c6d8f0b1
Revises: 7f716a66f99b
"""

from __future__ import annotations

from alembic import op

revision: str = "e2a4c6d8f0b1"
down_revision: str | None = "7f716a66f99b"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE evidence_upload_v2_type_enum "
        "ADD VALUE IF NOT EXISTS 'FOREIGN_FLOW_1W'"
    )
    op.execute(
        "ALTER TYPE evidence_upload_v2_type_enum "
        "ADD VALUE IF NOT EXISTS 'BROKER_FLOW_1D'"
    )


def downgrade() -> None:
    # PostgreSQL enum-value removal requires rebuilding the enum and every
    # dependent column. Keeping the additive values is the safe, data-preserving
    # downgrade behavior for this migration.
    pass
