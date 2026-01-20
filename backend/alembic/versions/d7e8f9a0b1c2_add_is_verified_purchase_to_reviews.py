"""add missing columns to reviews and addresses tables

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-01-19 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = 'c6d7e8f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =============================================
    # REVIEWS TABLE - Add missing columns
    # =============================================
    
    # Add is_verified_purchase column to reviews table
    op.add_column('reviews', sa.Column('is_verified_purchase', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add is_approved column to reviews table
    op.add_column('reviews', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='true'))
    
    # Add helpful_count column to reviews table
    op.add_column('reviews', sa.Column('helpful_count', sa.Integer(), nullable=False, server_default='0'))
    
    # Add updated_at column to reviews table
    op.add_column('reviews', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    
    # =============================================
    # ADDRESSES TABLE - Add missing columns
    # =============================================
    
    # Add label column to addresses table
    op.add_column('addresses', sa.Column('label', sa.String(100), nullable=True))
    
    # Add created_at column to addresses table
    op.add_column('addresses', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))


def downgrade() -> None:
    # Drop reviews columns
    op.drop_column('reviews', 'is_verified_purchase')
    op.drop_column('reviews', 'is_approved')
    op.drop_column('reviews', 'helpful_count')
    op.drop_column('reviews', 'updated_at')
    
    # Drop addresses columns
    op.drop_column('addresses', 'label')
    op.drop_column('addresses', 'created_at')
