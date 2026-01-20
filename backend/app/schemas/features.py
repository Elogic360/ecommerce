"""
Pydantic schemas for v1.5 features.
Wishlists, Coupons, Loyalty, Notifications, Returns, Bundles, Shipping, Tax.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# =============================================================================
# WISHLIST SCHEMAS
# =============================================================================
class WishlistItemBase(BaseModel):
    product_id: int
    notify_on_price_drop: bool = True


class WishlistItemCreate(WishlistItemBase):
    pass


class WishlistItem(WishlistItemBase):
    id: int
    user_id: int
    added_at: datetime
    price_at_addition: Optional[Decimal] = None

    class Config:
        from_attributes = True


class WishlistResponse(BaseModel):
    items: List[WishlistItem]
    total: int


# =============================================================================
# COUPON SCHEMAS
# =============================================================================
class CouponBase(BaseModel):
    code: str = Field(..., max_length=50)
    description: Optional[str] = None
    discount_type: str = Field(..., pattern="^(percentage|fixed|free_shipping)$")
    discount_value: Decimal
    min_purchase_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    usage_limit: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    applicable_categories: List[int] = []
    applicable_products: List[int] = []
    is_active: bool = True


class CouponCreate(CouponBase):
    pass


class CouponUpdate(BaseModel):
    description: Optional[str] = None
    discount_value: Optional[Decimal] = None
    min_purchase_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    usage_limit: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    applicable_categories: Optional[List[int]] = None
    applicable_products: Optional[List[int]] = None
    is_active: Optional[bool] = None


class Coupon(CouponBase):
    id: int
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class CouponValidation(BaseModel):
    code: str
    cart_total: Decimal
    product_ids: List[int] = []
    category_ids: List[int] = []


class CouponValidationResult(BaseModel):
    valid: bool
    discount_amount: Decimal = Decimal("0")
    message: str
    coupon: Optional[Coupon] = None


# =============================================================================
# LOYALTY SCHEMAS
# =============================================================================
class LoyaltyPointBase(BaseModel):
    points: int
    transaction_type: str
    description: Optional[str] = None


class LoyaltyPointCreate(LoyaltyPointBase):
    user_id: int
    reference_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class LoyaltyPoint(LoyaltyPointBase):
    id: int
    user_id: int
    reference_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoyaltyBalance(BaseModel):
    total_points: int
    tier: str
    points_to_next_tier: int
    history: List[LoyaltyPoint]


class LoyaltyRedemption(BaseModel):
    points_to_redeem: int


# =============================================================================
# NOTIFICATION SCHEMAS
# =============================================================================
class NotificationBase(BaseModel):
    type: str = Field(..., max_length=50)
    title: str = Field(..., max_length=255)
    message: str
    data: Optional[dict] = None


class NotificationCreate(NotificationBase):
    user_id: int


class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationList(BaseModel):
    items: List[Notification]
    unread_count: int
    total: int


# =============================================================================
# PRODUCT VIEW / ANALYTICS SCHEMAS
# =============================================================================
class ProductViewCreate(BaseModel):
    product_id: int
    session_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    device_type: Optional[str] = None
    referrer: Optional[str] = None


class ProductViewStats(BaseModel):
    product_id: int
    total_views: int
    unique_users: int
    avg_duration: Optional[float] = None


class AnalyticsSummary(BaseModel):
    total_orders: int
    total_revenue: Decimal
    total_customers: int
    total_products: int
    orders_today: int
    revenue_today: Decimal
    top_products: List[dict]
    recent_orders: List[dict]


# =============================================================================
# RETURN REQUEST SCHEMAS
# =============================================================================
class ReturnRequestBase(BaseModel):
    reason: str = Field(..., max_length=255)
    description: Optional[str] = None


class ReturnRequestCreate(ReturnRequestBase):
    order_id: int


class ReturnRequestUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|approved|rejected|completed)$")
    refund_amount: Optional[Decimal] = None


class ReturnRequest(ReturnRequestBase):
    id: int
    order_id: int
    user_id: int
    status: str
    refund_amount: Optional[Decimal] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# SHIPPING ZONE SCHEMAS
# =============================================================================
class ShippingZoneBase(BaseModel):
    name: str = Field(..., max_length=255)
    countries: List[str]
    states: Optional[List[str]] = None
    postal_codes: Optional[List[str]] = None
    base_rate: Decimal
    per_item_rate: Decimal = Decimal("0")
    free_shipping_threshold: Optional[Decimal] = None
    estimated_days_min: Optional[int] = None
    estimated_days_max: Optional[int] = None
    is_active: bool = True


class ShippingZoneCreate(ShippingZoneBase):
    pass


class ShippingZoneUpdate(BaseModel):
    name: Optional[str] = None
    countries: Optional[List[str]] = None
    states: Optional[List[str]] = None
    postal_codes: Optional[List[str]] = None
    base_rate: Optional[Decimal] = None
    per_item_rate: Optional[Decimal] = None
    free_shipping_threshold: Optional[Decimal] = None
    estimated_days_min: Optional[int] = None
    estimated_days_max: Optional[int] = None
    is_active: Optional[bool] = None


class ShippingZone(ShippingZoneBase):
    id: int

    class Config:
        from_attributes = True


class ShippingEstimate(BaseModel):
    zone_id: int
    zone_name: str
    rate: Decimal
    estimated_days: str
    free_shipping: bool


# =============================================================================
# TAX RATE SCHEMAS
# =============================================================================
class TaxRateBase(BaseModel):
    country: str = Field(..., max_length=2)
    state: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    rate: Decimal = Field(..., ge=0, le=1)
    is_active: bool = True


class TaxRateCreate(TaxRateBase):
    pass


class TaxRate(TaxRateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# PRODUCT BUNDLE SCHEMAS
# =============================================================================
class BundleProductItem(BaseModel):
    product_id: int
    quantity: int = 1


class ProductBundleBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    discount_percentage: Optional[Decimal] = None
    is_active: bool = True


class ProductBundleCreate(ProductBundleBase):
    products: List[BundleProductItem]


class ProductBundleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_percentage: Optional[Decimal] = None
    is_active: Optional[bool] = None
    products: Optional[List[BundleProductItem]] = None


class ProductBundle(ProductBundleBase):
    id: int
    created_at: datetime
    products: List[BundleProductItem]

    class Config:
        from_attributes = True


# =============================================================================
# ABANDONED CART SCHEMAS
# =============================================================================
class AbandonedCart(BaseModel):
    id: int
    user_id: int
    cart_data: dict
    total_value: Optional[Decimal] = None
    abandoned_at: datetime
    recovery_email_sent: bool
    recovered: bool
    recovered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# PRICE HISTORY SCHEMAS
# =============================================================================
class PriceHistoryItem(BaseModel):
    id: int
    product_id: int
    price: Decimal
    original_price: Optional[Decimal] = None
    changed_at: datetime
    changed_by: Optional[int] = None
    reason: Optional[str] = None

    class Config:
        from_attributes = True
