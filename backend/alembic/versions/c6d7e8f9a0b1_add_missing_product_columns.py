"""add missing product columns

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-01-18 10:30:00.000000

This migration adds all columns that exist in the Product model but are missing
from the database, ensuring the model and database are in sync.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, None] = 'b5c6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add missing columns to products table to match the SQLAlchemy model"""
    
    # List of columns that may need to be added
    # Each tuple: (column_name, column_type, kwargs)
    product_columns = [
        ('slug', sa.String(255), {'nullable': True}),
        ('short_description', sa.String(500), {'nullable': True}),
        ('cost_price', sa.Numeric(10, 2), {'nullable': True}),
        ('low_stock_threshold', sa.Integer(), {'server_default': '10', 'nullable': True}),
        ('barcode', sa.String(100), {'nullable': True}),
        ('brand', sa.String(100), {'nullable': True}),
        ('is_digital', sa.Boolean(), {'server_default': 'false', 'nullable': True}),
        ('view_count', sa.Integer(), {'server_default': '0', 'nullable': True}),
        ('sales_count', sa.Integer(), {'server_default': '0', 'nullable': True}),
        ('weight', sa.Numeric(10, 2), {'nullable': True}),
        ('length', sa.Numeric(10, 2), {'nullable': True}),
        ('width', sa.Numeric(10, 2), {'nullable': True}),
        ('height', sa.Numeric(10, 2), {'nullable': True}),
        ('meta_title', sa.String(255), {'nullable': True}),
        ('meta_description', sa.String(500), {'nullable': True}),
        ('meta_keywords', sa.String(255), {'nullable': True}),
        ('thumbnail', sa.String(500), {'nullable': True}),
    ]
    
    # Add each column if it doesn't exist
    for col_name, col_type, col_kwargs in product_columns:
        if not column_exists('products', col_name):
            op.add_column('products', sa.Column(col_name, col_type, **col_kwargs))
    
    # Create indexes if they don't exist (we'll try and catch errors)
    try:
        if column_exists('products', 'slug'):
            op.create_index('ix_products_slug', 'products', ['slug'], unique=True, if_not_exists=True)
    except Exception:
        pass  # Index may already exist
    
    try:
        if column_exists('products', 'barcode'):
            op.create_index('ix_products_barcode', 'products', ['barcode'], unique=True, if_not_exists=True)
    except Exception:
        pass  # Index may already exist
    
    # Generate slugs for existing products that don't have one
    op.execute("""
        UPDATE products 
        SET slug = LOWER(REGEXP_REPLACE(REGEXP_REPLACE(name, '[^\\w\\s-]', '', 'g'), '[\\s]+', '-', 'g'))
        WHERE slug IS NULL OR slug = ''
    """)
    
    # Make slug unique by appending id where there are duplicates
    op.execute("""
        UPDATE products p1
        SET slug = p1.slug || '-' || p1.id::text
        WHERE EXISTS (
            SELECT 1 FROM products p2 
            WHERE p2.slug = p1.slug AND p2.id < p1.id
        )
    """)


def downgrade() -> None:
    """Remove the added columns"""
    columns_to_remove = [
        'slug', 'short_description', 'cost_price', 'low_stock_threshold',
        'barcode', 'brand', 'is_digital', 'view_count', 'sales_count',
        'weight', 'length', 'width', 'height', 'meta_title', 
        'meta_description', 'meta_keywords', 'thumbnail'
    ]
    
    # Drop indexes first
    try:
        op.drop_index('ix_products_slug', 'products')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_products_barcode', 'products')
    except Exception:
        pass
    
    # Drop columns
    for col_name in columns_to_remove:
        try:
            op.drop_column('products', col_name)
        except Exception:
            pass  # Column may not exist
