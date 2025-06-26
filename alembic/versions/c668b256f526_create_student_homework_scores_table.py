"""create_student_homework_scores_table

Revision ID: c668b256f526
Revises: ddc5bb277708
Create Date: 2025-06-25 18:04:07.110630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c668b256f526'
down_revision: Union[str, Sequence[str], None] = 'ddc5bb277708'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
