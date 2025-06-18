"""add_llm_token_usage_table

Revision ID: a7967d4d83db
Revises: 1c706d1e8b8f
Create Date: 2025-05-27 08:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = 'a7967d4d83db'
down_revision: Union[str, None] = '1c706d1e8b8f' # Placeholder - replace if causes issues
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'llm_token_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=func.now(), nullable=True), # Made server_default effective by making nullable=True or removing default here for op.execute
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_llm_token_usage_user_id')
    )
    # Set server_default for timestamp using op.alter_column if not directly supported in create_table for all DBs via SA,
    # or ensure the column definition in SA handles it. For now, assuming SA in create_table is fine.
    # Explicitly create indexes.
    op.create_index(op.f('ix_llm_token_usage_id'), 'llm_token_usage', ['id'], unique=False)
    op.create_index(op.f('ix_llm_token_usage_user_id'), 'llm_token_usage', ['user_id'], unique=False)
    op.create_index(op.f('ix_llm_token_usage_session_id'), 'llm_token_usage', ['session_id'], unique=False)
    op.create_index(op.f('ix_llm_token_usage_timestamp'), 'llm_token_usage', ['timestamp'], unique=False)
    op.create_index(op.f('ix_llm_token_usage_action'), 'llm_token_usage', ['action'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_llm_token_usage_action'), table_name='llm_token_usage')
    op.drop_index(op.f('ix_llm_token_usage_timestamp'), table_name='llm_token_usage')
    op.drop_index(op.f('ix_llm_token_usage_session_id'), table_name='llm_token_usage')
    op.drop_index(op.f('ix_llm_token_usage_user_id'), table_name='llm_token_usage')
    op.drop_index(op.f('ix_llm_token_usage_id'), table_name='llm_token_usage')
    op.drop_table('llm_token_usage')
