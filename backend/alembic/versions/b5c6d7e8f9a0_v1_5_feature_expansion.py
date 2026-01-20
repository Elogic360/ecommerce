"""v1.5 feature expansion - wishlists, coupons, loyalty, notifications, analytics

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
Create Date: 2026-01-18 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import ProgrammingError

# revision identifiers
revision = 'b5c6d7e8f9a0'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def safe_create_table(table_name, *columns, **kwargs):
    """Create table if it doesn't exist"""
    try:
        op.create_table(table_name, *columns, **kwargs)
    except ProgrammingError:
        pass


def safe_add_column(table_name, column):
    """Add column if it doesn't exist"""
    try:
        op.add_column(table_name, column)
    except ProgrammingError:
        pass


def safe_create_index(index_name, table_name, columns, **kwargs):
    """Create index if it doesn't exist"""
    try:
        op.create_index(index_name, table_name, columns, **kwargs)
    except ProgrammingError:
        pass


def upgrade() -> None:
    # =========================================================================
    # WISHLISTS
    # =========================================================================
    safe_create_table(
        'wishlists',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.BigInteger(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('price_at_addition', sa.Numeric(10, 2)),
        sa.Column('notify_on_price_drop', sa.Boolean(), server_default='true'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_wishlist_user_product'),
    )
    safe_create_index('idx_wishlists_user_id', 'wishlists', ['user_id'])
    safe_create_index('idx_wishlists_product_id', 'wishlists', ['product_id'])

    # =========================================================================
    # COUPONS
    # =========================================================================
    safe_create_table(
        'coupons',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('discount_type', sa.String(20), nullable=False),  # percentage, fixed, free_shipping
        sa.Column('discount_value', sa.Numeric(10, 2), nullable=False),
        sa.Column('min_purchase_amount', sa.Numeric(10, 2)),
        sa.Column('max_discount_amount', sa.Numeric(10, 2)),
        sa.Column('usage_limit', sa.Integer()),
        sa.Column('usage_count', sa.Integer(), server_default='0'),
        sa.Column('valid_from', sa.TIMESTAMP(timezone=True)),
        sa.Column('valid_until', sa.TIMESTAMP(timezone=True)),
        sa.Column('applicable_categories', postgresql.JSONB(), server_default='[]'),
        sa.Column('applicable_products', postgresql.JSONB(), server_default='[]'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.CheckConstraint("discount_type IN ('percentage', 'fixed', 'free_shipping')", name='coupons_discount_type_check'),
    )
    safe_create_index('idx_coupons_code', 'coupons', ['code'])
    safe_create_index('idx_coupons_valid_until', 'coupons', ['valid_until'])

    safe_create_table(
        'coupon_usage',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('coupon_id', sa.BigInteger(), sa.ForeignKey('coupons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='SET NULL')),
        sa.Column('discount_applied', sa.Numeric(10, 2)),
        sa.Column('used_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    safe_create_index('idx_coupon_usage_coupon_id', 'coupon_usage', ['coupon_id'])
    safe_create_index('idx_coupon_usage_user_id', 'coupon_usage', ['user_id'])

    # =========================================================================
    # LOYALTY POINTS
    # =========================================================================
    safe_create_table(
        'loyalty_points',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),  # earned, redeemed, expired, adjusted
        sa.Column('reference_id', sa.BigInteger()),
        sa.Column('description', sa.Text()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    safe_create_index('idx_loyalty_points_user_id', 'loyalty_points', ['user_id'])
    safe_create_index('idx_loyalty_points_expires_at', 'loyalty_points', ['expires_at'])

    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    safe_create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB()),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    safe_create_index('idx_notifications_user_id', 'notifications', ['user_id'])
    safe_create_index('idx_notifications_is_read', 'notifications', ['is_read'])

    # =========================================================================
    # PRODUCT VIEWS (analytics)
    # =========================================================================
    safe_create_table(
        'product_views',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('product_id', sa.BigInteger(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(255)),
        sa.Column('viewed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column('device_type', sa.String(50)),
        sa.Column('referrer', sa.Text()),
    )
    safe_create_index('idx_product_views_user_id', 'product_views', ['user_id'])
    safe_create_index('idx_product_views_product_id', 'product_views', ['product_id'])
    safe_create_index('idx_product_views_viewed_at', 'product_views', ['viewed_at'])

    # =========================================================================
    # PRICE HISTORY
    # =========================================================================
    safe_create_table(
        'price_history',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('product_id', sa.BigInteger(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('original_price', sa.Numeric(10, 2)),
        sa.Column('changed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('changed_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('reason', sa.String(255)),
    )
    safe_create_index('idx_price_history_product_id', 'price_history', ['product_id'])
    safe_create_index('idx_price_history_changed_at', 'price_history', ['changed_at'])

    # =========================================================================
    # ABANDONED CARTS
    # =========================================================================
    safe_create_table(
        'abandoned_carts',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cart_data', postgresql.JSONB(), nullable=False),
        sa.Column('total_value', sa.Numeric(10, 2)),
        sa.Column('abandoned_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('recovery_email_sent', sa.Boolean(), server_default='false'),
        sa.Column('recovered', sa.Boolean(), server_default='false'),
        sa.Column('recovered_at', sa.TIMESTAMP(timezone=True)),
    )
    safe_create_index('idx_abandoned_carts_user_id', 'abandoned_carts', ['user_id'])
    safe_create_index('idx_abandoned_carts_abandoned_at', 'abandoned_carts', ['abandoned_at'])

    # =========================================================================
    # SHIPPING ZONES
    # =========================================================================
    safe_create_table(
        'shipping_zones',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('countries', postgresql.JSONB(), nullable=False),
        sa.Column('states', postgresql.JSONB()),
        sa.Column('postal_codes', postgresql.JSONB()),
        sa.Column('base_rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('per_item_rate', sa.Numeric(10, 2), server_default='0'),
        sa.Column('free_shipping_threshold', sa.Numeric(10, 2)),
        sa.Column('estimated_days_min', sa.Integer()),
        sa.Column('estimated_days_max', sa.Integer()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
    )

    # =========================================================================
    # TAX RATES
    # =========================================================================
    safe_create_table(
        'tax_rates',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('country', sa.String(2), nullable=False),
        sa.Column('state', sa.String(100)),
        sa.Column('city', sa.String(100)),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('rate', sa.Numeric(5, 4), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    safe_create_index('idx_tax_rates_location', 'tax_rates', ['country', 'state', 'city'])

    # =========================================================================
    # RETURN REQUESTS
    # =========================================================================
    safe_create_table(
        'return_requests',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reason', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(50), server_default=sa.text("'pending'")),
        sa.Column('refund_amount', sa.Numeric(10, 2)),
        sa.Column('approved_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'completed')", name='return_requests_status_check'),
    )
    safe_create_index('idx_return_requests_order_id', 'return_requests', ['order_id'])
    safe_create_index('idx_return_requests_status', 'return_requests', ['status'])

    # =========================================================================
    # PRODUCT BUNDLES
    # =========================================================================
    safe_create_table(
        'product_bundles',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('discount_percentage', sa.Numeric(5, 2)),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )

    safe_create_table(
        'bundle_products',
        sa.Column('bundle_id', sa.BigInteger(), sa.ForeignKey('product_bundles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('product_id', sa.BigInteger(), sa.ForeignKey('products.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('quantity', sa.Integer(), server_default='1'),
    )

    # =========================================================================
    # USER ENHANCEMENTS
    # =========================================================================
    safe_add_column('users', sa.Column('loyalty_tier', sa.String(50), server_default=sa.text("'bronze'")))
    safe_add_column('users', sa.Column('loyalty_points', sa.Integer(), server_default=sa.text('0')))
    safe_add_column('users', sa.Column('last_seen_at', sa.TIMESTAMP(timezone=True)))
    safe_add_column('users', sa.Column('preferred_currency', sa.String(3), server_default=sa.text("'USD'")))
    safe_add_column('users', sa.Column('phone_number', sa.String(20)))

    safe_create_index('idx_users_loyalty_tier', 'users', ['loyalty_tier'])

    # =========================================================================
    # PRODUCT ENHANCEMENTS
    # =========================================================================
    safe_add_column('products', sa.Column('view_count', sa.Integer(), server_default='0'))
    safe_add_column('products', sa.Column('tags', postgresql.JSONB(), server_default='[]'))
    safe_add_column('products', sa.Column('meta_title', sa.String(255)))
    safe_add_column('products', sa.Column('meta_description', sa.Text()))
    safe_add_column('products', sa.Column('weight', sa.Numeric(8, 2)))
    safe_add_column('products', sa.Column('dimensions', postgresql.JSONB()))

    safe_create_index('idx_products_view_count', 'products', ['view_count'])
    safe_create_index('idx_products_tags', 'products', ['tags'], postgresql_using='gin')

    # =========================================================================
    # ORDER ENHANCEMENTS
    # =========================================================================
    safe_add_column('orders', sa.Column('tracking_number', sa.String(255)))
    safe_add_column('orders', sa.Column('carrier', sa.String(100)))
    safe_add_column('orders', sa.Column('estimated_delivery', sa.TIMESTAMP(timezone=True)))
    safe_add_column('orders', sa.Column('coupon_code', sa.String(50)))
    safe_add_column('orders', sa.Column('discount_amount', sa.Numeric(10, 2), server_default='0'))
    safe_add_column('orders', sa.Column('loyalty_points_earned', sa.Integer(), server_default='0'))
    safe_add_column('orders', sa.Column('loyalty_points_used', sa.Integer(), server_default='0'))

    safe_create_index('idx_orders_tracking_number', 'orders', ['tracking_number'])


def downgrade() -> None:
    # Drop order enhancements
    op.drop_index('idx_orders_tracking_number', 'orders')
    op.drop_column('orders', 'loyalty_points_used')
    op.drop_column('orders', 'loyalty_points_earned')
    op.drop_column('orders', 'discount_amount')
    op.drop_column('orders', 'coupon_code')
    op.drop_column('orders', 'estimated_delivery')
    op.drop_column('orders', 'carrier')
    op.drop_column('orders', 'tracking_number')

    # Drop product enhancements
    op.drop_index('idx_products_tags', 'products')
    op.drop_index('idx_products_view_count', 'products')
    op.drop_column('products', 'dimensions')
    op.drop_column('products', 'weight')
    op.drop_column('products', 'meta_description')
    op.drop_column('products', 'meta_title')
    op.drop_column('products', 'tags')
    op.drop_column('products', 'view_count')

    # Drop user enhancements
    op.drop_index('idx_users_loyalty_tier', 'users')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'preferred_currency')
    op.drop_column('users', 'last_seen_at')
    op.drop_column('users', 'loyalty_points')
    op.drop_column('users', 'loyalty_tier')

    # Drop new tables
    op.drop_table('bundle_products')
    op.drop_table('product_bundles')
    op.drop_table('return_requests')
    op.drop_table('tax_rates')
    op.drop_table('shipping_zones')
    op.drop_table('abandoned_carts')
    op.drop_table('price_history')
    op.drop_table('product_views')
    op.drop_table('notifications')
    op.drop_table('loyalty_points')
    op.drop_table('coupon_usage')
    op.drop_table('coupons')
    op.drop_table('wishlists')
