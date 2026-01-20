"""enhance product and category models

Revision ID: 9c4f7d5e3b2a
Revises: 8b3f6e4c2d1a
Create Date: 2026-01-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4f7d5e3b2a'
down_revision: Union[str, None] = '8b3f6e4c2d1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enhance products and categories tables with additional fields"""
    
    # =========================================================================
    # PRODUCTS TABLE ENHANCEMENTS
    # =========================================================================
    
    # Add new columns to products
    op.add_column('products', sa.Column('slug', sa.String(255), nullable=True))
    op.add_column('products', sa.Column('short_description', sa.String(500), nullable=True))
    op.add_column('products', sa.Column('cost_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('products', sa.Column('low_stock_threshold', sa.Integer(), server_default='10', nullable=True))
    op.add_column('products', sa.Column('barcode', sa.String(100), nullable=True))
    op.add_column('products', sa.Column('is_digital', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('products', sa.Column('view_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('products', sa.Column('sales_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('products', sa.Column('thumbnail', sa.String(500), nullable=True))
    
    # Physical attributes
    op.add_column('products', sa.Column('weight', sa.Numeric(10, 2), nullable=True))
    op.add_column('products', sa.Column('length', sa.Numeric(10, 2), nullable=True))
    op.add_column('products', sa.Column('width', sa.Numeric(10, 2), nullable=True))
    op.add_column('products', sa.Column('height', sa.Numeric(10, 2), nullable=True))
    
    # SEO fields
    op.add_column('products', sa.Column('meta_title', sa.String(255), nullable=True))
    op.add_column('products', sa.Column('meta_description', sa.String(500), nullable=True))
    op.add_column('products', sa.Column('meta_keywords', sa.String(255), nullable=True))
    
    # Create indexes
    op.create_index('ix_products_slug', 'products', ['slug'], unique=True)
    op.create_index('ix_products_barcode', 'products', ['barcode'], unique=True)
    op.create_index('ix_products_name_search', 'products', ['name'])
    op.create_index('ix_products_price_range', 'products', ['price'])
    op.create_index('ix_products_active_featured', 'products', ['is_active', 'is_featured'])
    
    # =========================================================================
    # CATEGORIES TABLE ENHANCEMENTS
    # =========================================================================
    
    op.add_column('categories', sa.Column('slug', sa.String(100), nullable=True))
    op.add_column('categories', sa.Column('icon', sa.String(50), nullable=True))
    op.add_column('categories', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.add_column('categories', sa.Column('sort_order', sa.Integer(), server_default='0', nullable=True))
    op.add_column('categories', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('categories', sa.Column('meta_title', sa.String(255), nullable=True))
    op.add_column('categories', sa.Column('meta_description', sa.String(500), nullable=True))
    op.add_column('categories', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    op.add_column('categories', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    
    # Create foreign key for parent category
    op.create_foreign_key(
        'fk_categories_parent_id',
        'categories', 'categories',
        ['parent_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for slug
    op.create_index('ix_categories_slug', 'categories', ['slug'], unique=True)
    
    # =========================================================================
    # PRODUCT IMAGES TABLE ENHANCEMENTS
    # =========================================================================
    
    op.add_column('product_images', sa.Column('thumbnail_url', sa.String(500), nullable=True))
    op.add_column('product_images', sa.Column('sort_order', sa.Integer(), server_default='0', nullable=True))
    op.add_column('product_images', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('product_images', sa.Column('width', sa.Integer(), nullable=True))
    op.add_column('product_images', sa.Column('height', sa.Integer(), nullable=True))
    op.add_column('product_images', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    
    # =========================================================================
    # PRODUCT VARIATIONS TABLE ENHANCEMENTS
    # =========================================================================
    
    op.add_column('product_variations', sa.Column('image_url', sa.String(500), nullable=True))
    op.add_column('product_variations', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True))
    
    # =========================================================================
    # REVIEWS TABLE ENHANCEMENTS
    # =========================================================================
    
    op.add_column('reviews', sa.Column('is_verified_purchase', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('reviews', sa.Column('is_approved', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('reviews', sa.Column('helpful_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('reviews', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    
    # Create index for reviews
    op.create_index('ix_reviews_product_rating', 'reviews', ['product_id', 'rating'])


def downgrade() -> None:
    """Remove enhanced fields from products and categories tables"""
    
    # Reviews
    op.drop_index('ix_reviews_product_rating', table_name='reviews')
    op.drop_column('reviews', 'updated_at')
    op.drop_column('reviews', 'helpful_count')
    op.drop_column('reviews', 'is_approved')
    op.drop_column('reviews', 'is_verified_purchase')
    
    # Product variations
    op.drop_column('product_variations', 'is_active')
    op.drop_column('product_variations', 'image_url')
    
    # Product images
    op.drop_column('product_images', 'created_at')
    op.drop_column('product_images', 'height')
    op.drop_column('product_images', 'width')
    op.drop_column('product_images', 'file_size')
    op.drop_column('product_images', 'sort_order')
    op.drop_column('product_images', 'thumbnail_url')
    
    # Categories
    op.drop_index('ix_categories_slug', table_name='categories')
    op.drop_constraint('fk_categories_parent_id', 'categories', type_='foreignkey')
    op.drop_column('categories', 'updated_at')
    op.drop_column('categories', 'created_at')
    op.drop_column('categories', 'meta_description')
    op.drop_column('categories', 'meta_title')
    op.drop_column('categories', 'is_active')
    op.drop_column('categories', 'sort_order')
    op.drop_column('categories', 'parent_id')
    op.drop_column('categories', 'icon')
    op.drop_column('categories', 'slug')
    
    # Products
    op.drop_index('ix_products_active_featured', table_name='products')
    op.drop_index('ix_products_price_range', table_name='products')
    op.drop_index('ix_products_name_search', table_name='products')
    op.drop_index('ix_products_barcode', table_name='products')
    op.drop_index('ix_products_slug', table_name='products')
    op.drop_column('products', 'meta_keywords')
    op.drop_column('products', 'meta_description')
    op.drop_column('products', 'meta_title')
    op.drop_column('products', 'height')
    op.drop_column('products', 'width')
    op.drop_column('products', 'length')
    op.drop_column('products', 'weight')
    op.drop_column('products', 'thumbnail')
    op.drop_column('products', 'sales_count')
    op.drop_column('products', 'view_count')
    op.drop_column('products', 'is_digital')
    op.drop_column('products', 'barcode')
    op.drop_column('products', 'low_stock_threshold')
    op.drop_column('products', 'cost_price')
    op.drop_column('products', 'short_description')
    op.drop_column('products', 'slug')
