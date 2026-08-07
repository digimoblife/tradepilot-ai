"""merge archive and current_price heads

Revision ID: 7f716a66f99b
Revises: e1f2a3b4c5d6, a1b2c3d4e5f6
Create Date: 2026-08-07 21:49:45.399402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f716a66f99b'
down_revision: Union[str, Sequence[str], None] = ('e1f2a3b4c5d6', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
