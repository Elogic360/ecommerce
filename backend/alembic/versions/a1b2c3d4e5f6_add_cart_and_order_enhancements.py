"""Add cart and order enhancements

Revision ID: a1b2c3d4e5f6
Revises: 9c4f7d5e3b2a
Create Date: 2026-01-17

This migration adds:
- New 'carts' table for grouping cart items
- Enhanced cart_items with cart_id, unit_price, reservation fields
- Enhanced orders with guest fields, payment gateway fields, tracking
- New order_items fields for product snapshots
- New order_status_history table for audit trail
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9c4f7d5e3b2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # CREATE CARTS TABLE
    # =========================================================================
    op.create_table(
        'carts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=True, server_default='0'),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=True, server_default='0'),
        sa.Column('discount_amount', sa.Numeric(12, 2), nullable=True, server_default='0'),
        sa.Column('total', sa.Numeric(12, 2), nullable=True, server_default='0'),
        sa.Column('promo_code', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_carts_id', 'carts', ['id'], unique=False)
    op.create_index('ix_carts_user_id', 'carts', ['user_id'], unique=False)
    op.create_index('ix_carts_session_id', 'carts', ['session_id'], unique=True)
    op.create_index('ix_carts_user_active', 'carts', ['user_id', 'status'], unique=False)
    op.create_index('ix_carts_session_active', 'carts', ['session_id', 'status'], unique=False)
    op.create_index('ix_carts_expires', 'carts', ['expires_at'], unique=False)
    
    # =========================================================================
    # ENHANCE CART_ITEMS TABLE
    # =========================================================================
    # Add cart_id column (nullable initially for migration)
    op.add_column('cart_items', sa.Column('cart_id', sa.Integer(), nullable=True))
    op.add_column('cart_items', sa.Column('unit_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('cart_items', sa.Column('is_reserved', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('cart_items', sa.Column('reserved_until', sa.DateTime(timezone=True), nullable=True))
    
    # Make user_id nullable (for session carts via cart_id)
    op.alter_column('cart_items', 'user_id', nullable=True)
    
    # Add foreign key for cart_id
    op.create_foreign_key(
        'fk_cart_items_cart_id',
        'cart_items', 'carts',
        ['cart_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create indexes
    op.create_index('ix_cart_items_cart_id', 'cart_items', ['cart_id'], unique=False)
    op.create_index('ix_cart_items_cart_product', 'cart_items', ['cart_id', 'product_id', 'variation_id'], unique=False)
    
    # =========================================================================
    # ENHANCE ORDERS TABLE
    # =========================================================================
    # Make user_id nullable (for guest orders)
    op.alter_column('orders', 'user_id', nullable=True)
    op.alter_column('orders', 'address_id', nullable=True)
    
    # Add new columns
    op.add_column('orders', sa.Column('subtotal', sa.Numeric(12, 2), nullable=True, server_default='0'))
    op.add_column('orders', sa.Column('discount_amount', sa.Numeric(12, 2), nullable=True, server_default='0'))
    op.add_column('orders', sa.Column('promo_code', sa.String(50), nullable=True))
    op.add_column('orders', sa.Column('promo_discount', sa.Numeric(12, 2), nullable=True, server_default='0'))
    
    # Payment gateway fields
    op.add_column('orders', sa.Column('payment_transaction_id', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('payment_gateway', sa.String(50), nullable=True))
    op.add_column('orders', sa.Column('payment_intent_id', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('payment_metadata', sa.Text(), nullable=True))
    
    # Shipping tracking
    op.add_column('orders', sa.Column('tracking_number', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('shipping_carrier', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('shipped_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True))
    
    # Guest order info
    op.add_column('orders', sa.Column('guest_email', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('guest_name', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('guest_phone', sa.String(50), nullable=True))
    
    # Admin notes
    op.add_column('orders', sa.Column('admin_notes', sa.Text(), nullable=True))
    
    # Cancellation
    op.add_column('orders', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('cancelled_by', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('cancellation_reason', sa.Text(), nullable=True))
    
    # Email notification tracking
    op.add_column('orders', sa.Column('confirmation_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('shipping_notification_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('delivery_notification_sent_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add foreign key for cancelled_by
    op.create_foreign_key(
        'fk_orders_cancelled_by',
        'orders', 'users',
        ['cancelled_by'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes
    op.create_index('ix_orders_guest_email', 'orders', ['guest_email'], unique=False)
    op.create_index('ix_orders_user_status', 'orders', ['user_id', 'status'], unique=False)
    op.create_index('ix_orders_payment_status', 'orders', ['payment_status'], unique=False)
    
    # =========================================================================
    # ENHANCE ORDER_ITEMS TABLE
    # =========================================================================
    # Add product snapshot fields
    op.add_column('order_items', sa.Column('product_name', sa.String(255), nullable=True))
    op.add_column('order_items', sa.Column('product_sku', sa.String(100), nullable=True))
    op.add_column('order_items', sa.Column('product_image', sa.String(500), nullable=True))
    
    # Rename price to unit_price for consistency
    op.alter_column('order_items', 'price', new_column_name='unit_price')
    
    # Add additional pricing fields
    op.add_column('order_items', sa.Column('original_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('order_items', sa.Column('discount', sa.Numeric(10, 2), nullable=True, server_default='0'))
    op.add_column('order_items', sa.Column('subtotal', sa.Numeric(12, 2), nullable=True))
    op.add_column('order_items', sa.Column('tax', sa.Numeric(10, 2), nullable=True, server_default='0'))
    op.add_column('order_items', sa.Column('total', sa.Numeric(12, 2), nullable=True))
    
    # Item status
    op.add_column('order_items', sa.Column('status', sa.String(30), nullable=True, server_default='pending'))
    
    # Timestamps
    op.add_column('order_items', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    
    # =========================================================================
    # CREATE ORDER_STATUS_HISTORY TABLE
    # =========================================================================
    op.create_table(
        'order_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('from_status', sa.String(30), nullable=True),
        sa.Column('to_status', sa.String(30), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_order_status_history_id', 'order_status_history', ['id'], unique=False)
    op.create_index('ix_order_status_history_order_id', 'order_status_history', ['order_id'], unique=False)


def downgrade() -> None:
    # Drop order_status_history table
    op.drop_index('ix_order_status_history_order_id', table_name='order_status_history')
    op.drop_index('ix_order_status_history_id', table_name='order_status_history')
    op.drop_table('order_status_history')
    
    # Revert order_items changes
    op.drop_column('order_items', 'created_at')
    op.drop_column('order_items', 'status')
    op.drop_column('order_items', 'total')
    op.drop_column('order_items', 'tax')
    op.drop_column('order_items', 'subtotal')
    op.drop_column('order_items', 'discount')
    op.drop_column('order_items', 'original_price')
    op.alter_column('order_items', 'unit_price', new_column_name='price')
    op.drop_column('order_items', 'product_image')
    op.drop_column('order_items', 'product_sku')
    op.drop_column('order_items', 'product_name')
    
    # Revert orders changes
    op.drop_index('ix_orders_payment_status', table_name='orders')
    op.drop_index('ix_orders_user_status', table_name='orders')
    op.drop_index('ix_orders_guest_email', table_name='orders')
    op.drop_constraint('fk_orders_cancelled_by', 'orders', type_='foreignkey')
    op.drop_column('orders', 'delivery_notification_sent_at')
    op.drop_column('orders', 'shipping_notification_sent_at')
    op.drop_column('orders', 'confirmation_sent_at')
    op.drop_column('orders', 'cancellation_reason')
    op.drop_column('orders', 'cancelled_by')
    op.drop_column('orders', 'cancelled_at')
    op.drop_column('orders', 'admin_notes')
    op.drop_column('orders', 'guest_phone')
    op.drop_column('orders', 'guest_name')
    op.drop_column('orders', 'guest_email')
    op.drop_column('orders', 'delivered_at')
    op.drop_column('orders', 'shipped_at')
    op.drop_column('orders', 'shipping_carrier')
    op.drop_column('orders', 'tracking_number')
    op.drop_column('orders', 'payment_metadata')
    op.drop_column('orders', 'payment_intent_id')
    op.drop_column('orders', 'payment_gateway')
    op.drop_column('orders', 'payment_transaction_id')
    op.drop_column('orders', 'promo_discount')
    op.drop_column('orders', 'promo_code')
    op.drop_column('orders', 'discount_amount')
    op.drop_column('orders', 'subtotal')
    op.alter_column('orders', 'address_id', nullable=False)
    op.alter_column('orders', 'user_id', nullable=False)
    
    # Revert cart_items changes
    op.drop_index('ix_cart_items_cart_product', table_name='cart_items')
    op.drop_index('ix_cart_items_cart_id', table_name='cart_items')
    op.drop_constraint('fk_cart_items_cart_id', 'cart_items', type_='foreignkey')
    op.alter_column('cart_items', 'user_id', nullable=False)
    op.drop_column('cart_items', 'reserved_until')
    op.drop_column('cart_items', 'is_reserved')
    op.drop_column('cart_items', 'unit_price')
    op.drop_column('cart_items', 'cart_id')
    
    # Drop carts table
    op.drop_index('ix_carts_expires', table_name='carts')
    op.drop_index('ix_carts_session_active', table_name='carts')
    op.drop_index('ix_carts_user_active', table_name='carts')
    op.drop_index('ix_carts_session_id', table_name='carts')
    op.drop_index('ix_carts_user_id', table_name='carts')
    op.drop_index('ix_carts_id', table_name='carts')
    op.drop_table('carts')
