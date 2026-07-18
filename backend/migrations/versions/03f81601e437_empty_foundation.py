"""empty foundation

Revision ID: 03f81601e437
Revises:
Create Date: 2026-07-18 09:21:45.374255

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "03f81601e437"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
