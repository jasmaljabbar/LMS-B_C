"""create_notifications_table

Revision ID: ddc5bb277708
Revises: 3173921e7b44
Create Date: 2025-06-25 16:11:47.198470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ddc5bb277708'
down_revision: Union[str, Sequence[str], None] = '3173921e7b44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
