"""p21 evidence batch integrity

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
Create Date: 2026-07-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_evidence_batches_one_draft_per_session_analysis",
        "evidence_batches",
        ["session_id", "analysis_type"],
        unique=True,
        postgresql_where=sa.text("status = 'DRAFT'::evidence_batch_status_enum"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_evidence_batches_one_draft_per_session_analysis",
        table_name="evidence_batches",
    )
