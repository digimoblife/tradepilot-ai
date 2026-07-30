"""Add WAIT Update metadata to rebuild evidence uploads.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_uploads_v2",
        sa.Column("current_price", sa.Numeric(precision=20, scale=6), nullable=True),
    )
    op.add_column(
        "evidence_uploads_v2",
        sa.Column("observation_timestamp", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence_uploads_v2", "observation_timestamp")
    op.drop_column("evidence_uploads_v2", "current_price")
