"""P4: Add monitoring_slot column to evidence_batches.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-27

Adds an application-owned monitoring_slot column to the evidence_batches
table. The slot is set by the user when preparing an OPEN_POSITION_UPDATE
batch and is stored as a plain VARCHAR so no enum migration is required.

Valid application-level values: MORNING, MIDDAY, CLOSE, UNSPECIFIED
NULL is treated identically to UNSPECIFIED (slot not yet chosen).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str = "d4e5f6a7b8c9"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_batches",
        sa.Column(
            "monitoring_slot",
            sa.String(20),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("evidence_batches", "monitoring_slot")
