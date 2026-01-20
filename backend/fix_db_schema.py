"""Script to safely add missing tables and columns to the database.
Run this directly with: python fix_db_schema.py
"""
import psycopg2
from psycopg2.extras import DictCursor
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection string from .env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ecommerce_user:commercePASS@localhost:5432/ecommerce")

def get_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)


def execute_safe(cursor, sql, description):
    """Execute SQL and handle errors gracefully"""
    try:
        cursor.execute(sql)
        print(f"✓ {description}")
        return True
    except psycopg2.errors.DuplicateTable:
        print(f"  (exists) {description}")
        return True
    except psycopg2.errors.DuplicateColumn:
        print(f"  (exists) {description}")
        return True
    except psycopg2.errors.DuplicateObject:
        print(f"  (exists) {description}")
        return True
    except Exception as e:
        print(f"✗ {description}: {e}")
        return False


def main():
    conn = get_connection()
    conn.autocommit = True  # Important: each statement is its own transaction
    cursor = conn.cursor()
    
    print("=" * 60)
    print("Fixing Database Schema for V1.5 Features")
    print("=" * 60)
    
    # =========================================================================
    # TABLES
    # =========================================================================
    
    print("\n--- Creating Tables ---")
    
    # Wishlists
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS wishlists (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            added_at TIMESTAMPTZ DEFAULT NOW(),
            price_at_addition DECIMAL(10, 2),
            notify_on_price_drop BOOLEAN DEFAULT true,
            UNIQUE(user_id, product_id)
        )
    """, "Create wishlists table")
    
    # Coupons
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS coupons (
            id BIGSERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('percentage', 'fixed', 'free_shipping')),
            discount_value DECIMAL(10, 2) NOT NULL,
            min_purchase_amount DECIMAL(10, 2),
            max_discount_amount DECIMAL(10, 2),
            usage_limit INTEGER,
            usage_count INTEGER DEFAULT 0,
            valid_from TIMESTAMPTZ,
            valid_until TIMESTAMPTZ,
            applicable_categories JSONB DEFAULT '[]',
            applicable_products JSONB DEFAULT '[]',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """, "Create coupons table")
    
    # Coupon Usage
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS coupon_usage (
            id BIGSERIAL PRIMARY KEY,
            coupon_id BIGINT NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            order_id BIGINT REFERENCES orders(id) ON DELETE SET NULL,
            discount_applied DECIMAL(10, 2),
            used_at TIMESTAMPTZ DEFAULT NOW()
        )
    """, "Create coupon_usage table")
    
    # Loyalty Points
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS loyalty_points (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            points INTEGER NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            reference_id BIGINT,
            description TEXT,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """, "Create loyalty_points table")
    
    # Notifications
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS notifications (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            data JSONB,
            is_read BOOLEAN DEFAULT false,
            sent_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """, "Create notifications table")
    
    # Product Views
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS product_views (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            session_id VARCHAR(255),
            viewed_at TIMESTAMPTZ DEFAULT NOW(),
            duration_seconds INTEGER,
            device_type VARCHAR(50),
            referrer TEXT
        )
    """, "Create product_views table")
    
    # Price History
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS price_history (
            id BIGSERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            price DECIMAL(10, 2) NOT NULL,
            original_price DECIMAL(10, 2),
            changed_at TIMESTAMPTZ DEFAULT NOW(),
            changed_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
            reason VARCHAR(255)
        )
    """, "Create price_history table")
    
    # Abandoned Carts
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS abandoned_carts (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            cart_data JSONB NOT NULL,
            total_value DECIMAL(10, 2),
            abandoned_at TIMESTAMPTZ DEFAULT NOW(),
            recovery_email_sent BOOLEAN DEFAULT false,
            recovered BOOLEAN DEFAULT false,
            recovered_at TIMESTAMPTZ
        )
    """, "Create abandoned_carts table")
    
    # Shipping Zones
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS shipping_zones (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            countries JSONB NOT NULL,
            states JSONB,
            postal_codes JSONB,
            base_rate DECIMAL(10, 2) NOT NULL,
            per_item_rate DECIMAL(10, 2) DEFAULT 0,
            free_shipping_threshold DECIMAL(10, 2),
            estimated_days_min INTEGER,
            estimated_days_max INTEGER,
            is_active BOOLEAN DEFAULT true
        )
    """, "Create shipping_zones table")
    
    # Tax Rates
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS tax_rates (
            id BIGSERIAL PRIMARY KEY,
            country VARCHAR(2) NOT NULL,
            state VARCHAR(100),
            city VARCHAR(100),
            postal_code VARCHAR(20),
            rate DECIMAL(5, 4) NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """, "Create tax_rates table")
    
    # Return Requests
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS return_requests (
            id BIGSERIAL PRIMARY KEY,
            order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reason VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'completed')),
            refund_amount DECIMAL(10, 2),
            approved_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
            approved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """, "Create return_requests table")
    
    # Product Bundles
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS product_bundles (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            discount_percentage DECIMAL(5, 2),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """, "Create product_bundles table")
    
    # Bundle Products
    execute_safe(cursor, """
        CREATE TABLE IF NOT EXISTS bundle_products (
            bundle_id BIGINT NOT NULL REFERENCES product_bundles(id) ON DELETE CASCADE,
            product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (bundle_id, product_id)
        )
    """, "Create bundle_products table")
    
    # =========================================================================
    # USER COLUMNS
    # =========================================================================
    
    print("\n--- Adding User Columns ---")
    
    execute_safe(cursor, "ALTER TABLE users ADD COLUMN IF NOT EXISTS loyalty_tier VARCHAR(50) DEFAULT 'bronze'", 
                 "Add users.loyalty_tier")
    execute_safe(cursor, "ALTER TABLE users ADD COLUMN IF NOT EXISTS loyalty_points INTEGER DEFAULT 0", 
                 "Add users.loyalty_points")
    execute_safe(cursor, "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ", 
                 "Add users.last_seen_at")
    execute_safe(cursor, "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_currency VARCHAR(3) DEFAULT 'USD'", 
                 "Add users.preferred_currency")
    execute_safe(cursor, "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)", 
                 "Add users.phone_number")
    
    # =========================================================================
    # PRODUCT COLUMNS
    # =========================================================================
    
    print("\n--- Adding Product Columns ---")
    
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS slug VARCHAR(255)", 
                 "Add products.slug")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS brand VARCHAR(100)", 
                 "Add products.brand")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS short_description VARCHAR(500)", 
                 "Add products.short_description")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS original_price DECIMAL(10,2)", 
                 "Add products.original_price")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS sale_price DECIMAL(10,2)", 
                 "Add products.sale_price")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS average_rating DECIMAL(3,2) DEFAULT 0", 
                 "Add products.average_rating")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0", 
                 "Add products.review_count")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT false", 
                 "Add products.is_featured")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_new BOOLEAN DEFAULT false", 
                 "Add products.is_new")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_bestseller BOOLEAN DEFAULT false", 
                 "Add products.is_bestseller")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS metadata JSONB", 
                 "Add products.metadata")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0", 
                 "Add products.view_count")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'", 
                 "Add products.tags")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_title VARCHAR(255)", 
                 "Add products.meta_title")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_description TEXT", 
                 "Add products.meta_description")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS weight DECIMAL(8, 2)", 
                 "Add products.weight")
    execute_safe(cursor, "ALTER TABLE products ADD COLUMN IF NOT EXISTS dimensions JSONB", 
                 "Add products.dimensions")
    
    # =========================================================================
    # ORDER COLUMNS
    # =========================================================================
    
    print("\n--- Adding Order Columns ---")
    
    execute_safe(cursor, "ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(255)", 
                 "Add orders.tracking_number")
    execute_safe(cursor, "ALTER TABLE orders ADD COLUMN IF NOT EXISTS carrier VARCHAR(100)", 
                 "Add orders.carrier")
    execute_safe(cursor, "ALTER TABLE orders ADD COLUMN IF NOT EXISTS estimated_delivery TIMESTAMPTZ", 
                 "Add orders.estimated_delivery")
    execute_safe(cursor, "ALTER TABLE orders ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(50)", 
                 "Add orders.coupon_code")
    execute_safe(cursor, "ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10, 2) DEFAULT 0", 
                 "Add orders.discount_amount")
    execute_safe(cursor, "ALTER TABLE orders ADD COLUMN IF NOT EXISTS loyalty_points_earned INTEGER DEFAULT 0", 
                 "Add orders.loyalty_points_earned")
    execute_safe(cursor, "ALTER TABLE orders ADD COLUMN IF NOT EXISTS loyalty_points_used INTEGER DEFAULT 0", 
                 "Add orders.loyalty_points_used")
    
    # =========================================================================
    # INDEXES
    # =========================================================================
    
    print("\n--- Creating Indexes ---")
    
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_wishlists_user_id ON wishlists(user_id)", 
                 "Create idx_wishlists_user_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_wishlists_product_id ON wishlists(product_id)", 
                 "Create idx_wishlists_product_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(code)", 
                 "Create idx_coupons_code")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_coupons_valid_until ON coupons(valid_until)", 
                 "Create idx_coupons_valid_until")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_coupon_usage_coupon_id ON coupon_usage(coupon_id)", 
                 "Create idx_coupon_usage_coupon_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_coupon_usage_user_id ON coupon_usage(user_id)", 
                 "Create idx_coupon_usage_user_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_loyalty_points_user_id ON loyalty_points(user_id)", 
                 "Create idx_loyalty_points_user_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_loyalty_points_expires_at ON loyalty_points(expires_at)", 
                 "Create idx_loyalty_points_expires_at")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)", 
                 "Create idx_notifications_user_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)", 
                 "Create idx_notifications_is_read")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_product_views_user_id ON product_views(user_id)", 
                 "Create idx_product_views_user_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_product_views_product_id ON product_views(product_id)", 
                 "Create idx_product_views_product_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_product_views_viewed_at ON product_views(viewed_at)", 
                 "Create idx_product_views_viewed_at")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id)", 
                 "Create idx_price_history_product_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_price_history_changed_at ON price_history(changed_at)", 
                 "Create idx_price_history_changed_at")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_abandoned_carts_user_id ON abandoned_carts(user_id)", 
                 "Create idx_abandoned_carts_user_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_abandoned_carts_abandoned_at ON abandoned_carts(abandoned_at)", 
                 "Create idx_abandoned_carts_abandoned_at")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_tax_rates_location ON tax_rates(country, state, city)", 
                 "Create idx_tax_rates_location")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_return_requests_order_id ON return_requests(order_id)", 
                 "Create idx_return_requests_order_id")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_return_requests_status ON return_requests(status)", 
                 "Create idx_return_requests_status")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_users_loyalty_tier ON users(loyalty_tier)", 
                 "Create idx_users_loyalty_tier")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_products_view_count ON products(view_count)", 
                 "Create idx_products_view_count")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug)", 
                 "Create idx_products_slug")
    execute_safe(cursor, "CREATE INDEX IF NOT EXISTS idx_orders_tracking_number ON orders(tracking_number)", 
                 "Create idx_orders_tracking_number")
    
    # Try to create GIN index for tags (may not work on all setups)
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_tags ON products USING gin(tags)")
        print("✓ Create idx_products_tags (GIN)")
    except Exception as e:
        print(f"  (skipped) GIN index for tags: {e}")
    
    # =========================================================================
    # STAMP ALEMBIC
    # =========================================================================
    
    print("\n--- Updating Alembic Version ---")
    
    # Mark the v1.5 migration as completed
    try:
        # Check if alembic_version table exists
        cursor.execute("SELECT version_num FROM alembic_version")
        current = cursor.fetchone()
        if current:
            cursor.execute("UPDATE alembic_version SET version_num = 'c6d7e8f9a0b1'")
            print(f"✓ Updated alembic_version from {current[0]} to c6d7e8f9a0b1")
        else:
            cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('c6d7e8f9a0b1')")
            print("✓ Set alembic_version to c6d7e8f9a0b1")
    except Exception as e:
        print(f"  Warning: Could not update alembic_version: {e}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("Schema Fix Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
