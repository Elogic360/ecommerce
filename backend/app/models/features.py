"""
SQLAlchemy models for v1.5 feature expansion.
Wishlists, Coupons, Loyalty, Notifications, Analytics, Returns, Bundles, Shipping, Tax.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, Boolean, Numeric,
    ForeignKey, TIMESTAMP, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


# =============================================================================
# WISHLIST
# =============================================================================
class Wishlist(Base):
    __tablename__ = "wishlists"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    price_at_addition = Column(Numeric(10, 2))
    notify_on_price_drop = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    )

    user = relationship("User", back_populates="wishlists")
    product = relationship("Product", back_populates="wishlisted_by")


# =============================================================================
# COUPONS
# =============================================================================
class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(BigInteger, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    discount_type = Column(String(20), nullable=False)  # percentage, fixed, free_shipping
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_purchase_amount = Column(Numeric(10, 2))
    max_discount_amount = Column(Numeric(10, 2))
    usage_limit = Column(Integer)
    usage_count = Column(Integer, default=0)
    valid_from = Column(TIMESTAMP(timezone=True))
    valid_until = Column(TIMESTAMP(timezone=True), index=True)
    applicable_categories = Column(JSONB, default=[])
    applicable_products = Column(JSONB, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "discount_type IN ('percentage', 'fixed', 'free_shipping')",
            name="coupons_discount_type_check"
        ),
    )

    usages = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")


class CouponUsage(Base):
    __tablename__ = "coupon_usage"

    id = Column(BigInteger, primary_key=True, index=True)
    coupon_id = Column(BigInteger, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="SET NULL"))
    discount_applied = Column(Numeric(10, 2))
    used_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    coupon = relationship("Coupon", back_populates="usages")
    user = relationship("User", back_populates="coupon_usages")
    order = relationship("Order", back_populates="coupon_usage")


# =============================================================================
# LOYALTY POINTS
# =============================================================================
class LoyaltyPoint(Base):
    __tablename__ = "loyalty_points"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    points = Column(Integer, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # earned, redeemed, expired, adjusted
    reference_id = Column(BigInteger)
    description = Column(Text)
    expires_at = Column(TIMESTAMP(timezone=True), index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="loyalty_transactions")


# =============================================================================
# NOTIFICATIONS
# =============================================================================
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB)
    is_read = Column(Boolean, default=False, index=True)
    sent_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")


# =============================================================================
# PRODUCT VIEWS (ANALYTICS)
# =============================================================================
class ProductView(Base):
    __tablename__ = "product_views"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(255))
    viewed_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    duration_seconds = Column(Integer)
    device_type = Column(String(50))
    referrer = Column(Text)

    user = relationship("User", back_populates="product_views")
    product = relationship("Product", back_populates="views")


# =============================================================================
# PRICE HISTORY
# =============================================================================
class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(BigInteger, primary_key=True, index=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2))
    changed_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    changed_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    reason = Column(String(255))

    product = relationship("Product", back_populates="price_history")
    admin = relationship("User", foreign_keys=[changed_by])


# =============================================================================
# ABANDONED CARTS
# =============================================================================
class AbandonedCart(Base):
    __tablename__ = "abandoned_carts"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cart_data = Column(JSONB, nullable=False)
    total_value = Column(Numeric(10, 2))
    abandoned_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    recovery_email_sent = Column(Boolean, default=False)
    recovered = Column(Boolean, default=False)
    recovered_at = Column(TIMESTAMP(timezone=True))

    user = relationship("User", back_populates="abandoned_carts")


# =============================================================================
# SHIPPING ZONES
# =============================================================================
class ShippingZone(Base):
    __tablename__ = "shipping_zones"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    countries = Column(JSONB, nullable=False)
    states = Column(JSONB)
    postal_codes = Column(JSONB)
    base_rate = Column(Numeric(10, 2), nullable=False)
    per_item_rate = Column(Numeric(10, 2), default=0)
    free_shipping_threshold = Column(Numeric(10, 2))
    estimated_days_min = Column(Integer)
    estimated_days_max = Column(Integer)
    is_active = Column(Boolean, default=True)


# =============================================================================
# TAX RATES
# =============================================================================
class TaxRate(Base):
    __tablename__ = "tax_rates"

    id = Column(BigInteger, primary_key=True, index=True)
    country = Column(String(2), nullable=False)
    state = Column(String(100))
    city = Column(String(100))
    postal_code = Column(String(20))
    rate = Column(Numeric(5, 4), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


# =============================================================================
# RETURN REQUESTS
# =============================================================================
class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(BigInteger, primary_key=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending", index=True)
    refund_amount = Column(Numeric(10, 2))
    approved_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'completed')",
            name="return_requests_status_check"
        ),
    )

    order = relationship("Order", back_populates="return_requests")
    user = relationship("User", foreign_keys=[user_id], back_populates="return_requests")
    approver = relationship("User", foreign_keys=[approved_by])


# =============================================================================
# PRODUCT BUNDLES
# =============================================================================
class ProductBundle(Base):
    __tablename__ = "product_bundles"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    discount_percentage = Column(Numeric(5, 2))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    products = relationship("BundleProduct", back_populates="bundle", cascade="all, delete-orphan")


class BundleProduct(Base):
    __tablename__ = "bundle_products"

    bundle_id = Column(BigInteger, ForeignKey("product_bundles.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    quantity = Column(Integer, default=1)

    bundle = relationship("ProductBundle", back_populates="products")
    product = relationship("Product", back_populates="bundles")
