"""create_user_files_table

Revision ID: 992a05637508
Revises: c668b256f526
Create Date: 2025-06-26 13:06:25.611540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '992a05637508'
down_revision: Union[str, Sequence[str], None] = 'c668b256f526'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
