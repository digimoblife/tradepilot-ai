"""Add user-confirmed current price to evidence batches."""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evidence_batches", sa.Column("current_price", sa.Numeric(20, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence_batches", "current_price")
