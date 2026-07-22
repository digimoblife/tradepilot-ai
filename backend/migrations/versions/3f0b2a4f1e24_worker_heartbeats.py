"""create worker_heartbeats

Revision ID: 3f0b2a4f1e24
Revises: 8e4d747e19db
Create Date: 2026-07-22 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3f0b2a4f1e24"
down_revision: Union[str, Sequence[str], None] = "8e4d747e19db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'RUNNING'")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_worker_heartbeats")),
    )


def downgrade() -> None:
    op.drop_table("worker_heartbeats")
