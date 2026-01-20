"""
Order Schemas - Request/Response models for order management
"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum


# =============================================================================
# ENUMS (matching model enums)
# =============================================================================

class OrderStatusEnum(str, Enum):
    """Order status workflow"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    ON_HOLD = "on_hold"
    FAILED = "failed"


class PaymentStatusEnum(str, Enum):
    """Payment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"


class PaymentMethodEnum(str, Enum):
    """Supported payment methods"""
    CASH_ON_DELIVERY = "cod"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"


# =============================================================================
# ORDER ITEM SCHEMAS
# =============================================================================

class OrderItemBase(BaseModel):
    """Base order item fields"""
    product_id: int
    variation_id: Optional[int] = None
    quantity: int = Field(ge=1)


class OrderItemCreate(OrderItemBase):
    """Schema for creating order item"""
    pass


class OrderItemProductInfo(BaseModel):
    """Product info embedded in order item"""
    id: int
    name: str
    slug: Optional[str] = None
    sku: Optional[str] = None
    primary_image: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderItemResponse(BaseModel):
    """Order item response with product details"""
    id: int
    order_id: int
    product_id: Optional[int] = None
    variation_id: Optional[int] = None
    
    # Product snapshot
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_image: Optional[str] = None
    
    # Pricing
    quantity: int
    unit_price: Decimal
    original_price: Optional[Decimal] = None
    discount: Decimal = Decimal("0.00")
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    
    # Status
    status: str = "pending"
    
    # Product reference
    product: Optional[OrderItemProductInfo] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# ADDRESS SCHEMAS
# =============================================================================

class ShippingAddress(BaseModel):
    """Shipping address for order"""
    address_line_1: str = Field(min_length=5, max_length=255)
    address_line_2: Optional[str] = None
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)
    country: str = Field(min_length=2, max_length=100)
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    
    class Config:
        from_attributes = True


class Address(ShippingAddress):
    """Full address with ID"""
    id: int
    user_id: Optional[int] = None
    label: Optional[str] = None
    is_default: bool = False
    
    class Config:
        from_attributes = True


# =============================================================================
# ORDER CREATE SCHEMAS
# =============================================================================

class OrderBase(BaseModel):
    """Base order fields"""
    address_id: Optional[int] = None
    payment_method: str = PaymentMethodEnum.CASH_ON_DELIVERY.value
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    """Create order with items"""
    items: List[OrderItemCreate]


class OrderFromCart(BaseModel):
    """Create order from user's cart"""
    address_id: int
    payment_method: str = PaymentMethodEnum.CASH_ON_DELIVERY.value
    notes: Optional[str] = None
    promo_code: Optional[str] = None


class GuestOrderCreate(BaseModel):
    """Guest order creation (no auth required)"""
    # Guest info
    guest_email: EmailStr
    guest_name: str = Field(min_length=2, max_length=255)
    guest_phone: str = Field(min_length=5, max_length=50)
    
    # Shipping address
    address_line_1: str = Field(min_length=5, max_length=255)
    address_line_2: Optional[str] = None
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)
    country: str = Field(min_length=2, max_length=100)
    
    # Order items
    items: List[OrderItemCreate]
    
    # Payment
    payment_method: str = PaymentMethodEnum.CASH_ON_DELIVERY.value
    notes: Optional[str] = None


# =============================================================================
# ORDER UPDATE SCHEMAS
# =============================================================================

class OrderUpdate(BaseModel):
    """Update order (general)"""
    notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Update order status (admin only)"""
    status: OrderStatusEnum
    notes: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    """Update payment status"""
    payment_status: PaymentStatusEnum
    transaction_id: Optional[str] = None
    notes: Optional[str] = None


class ShippingUpdate(BaseModel):
    """Update shipping info"""
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None
    notes: Optional[str] = None


class CancelOrderRequest(BaseModel):
    """Request to cancel order"""
    reason: Optional[str] = None


# =============================================================================
# ORDER RESPONSE SCHEMAS
# =============================================================================

class OrderSummary(BaseModel):
    """Brief order summary for lists"""
    id: int
    order_number: str
    status: str
    payment_status: str
    total_amount: Decimal
    item_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Full order response"""
    id: int
    order_number: str
    user_id: Optional[int] = None
    
    # Status
    status: str
    payment_status: str
    
    # Amounts
    subtotal: Optional[Decimal] = None
    total_amount: Decimal
    shipping_cost: Decimal
    tax_amount: Decimal
    discount_amount: Decimal = Decimal("0.00")
    promo_code: Optional[str] = None
    
    # Payment
    payment_method: Optional[str] = None
    payment_transaction_id: Optional[str] = None
    payment_gateway: Optional[str] = None
    
    # Shipping
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # Guest info
    guest_email: Optional[str] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    
    # Notes
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Relationships
    items: List[OrderItemResponse] = []
    address: Optional[Address] = None
    
    # Computed
    item_count: int = 0
    is_cancellable: bool = True
    # Client instruction
    clear_client_cart: bool = True
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Paginated list of orders"""
    items: List[OrderSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# =============================================================================
# ORDER STATUS HISTORY
# =============================================================================

class OrderStatusHistoryResponse(BaseModel):
    """Status change history entry"""
    id: int
    order_id: int
    from_status: Optional[str] = None
    to_status: str
    changed_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# PAYMENT INTEGRATION SCHEMAS
# =============================================================================

class PaymentIntentCreate(BaseModel):
    """Create payment intent (Stripe)"""
    order_id: int
    payment_method_id: Optional[str] = None


class PaymentIntentResponse(BaseModel):
    """Payment intent response"""
    client_secret: str
    payment_intent_id: str
    amount: int  # in cents
    currency: str = "usd"
    status: str


class PaymentConfirmation(BaseModel):
    """Payment confirmation webhook data"""
    payment_intent_id: str
    status: str
    amount_received: int
    metadata: Optional[dict] = None


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

class Product(BaseModel):
    """Legacy product schema"""
    id: int
    name: str
    price: Decimal
    primary_image: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderItem(OrderItemBase):
    """Legacy order item (backward compatibility)"""
    id: int
    order_id: int
    price: Decimal
    product: Optional[Product] = None

    class Config:
        from_attributes = True


class Order(OrderBase):
    """Legacy order response (backward compatibility)"""
    id: int
    user_id: Optional[int] = None
    order_number: str
    total_amount: Decimal
    shipping_cost: Decimal
    tax_amount: Decimal
    status: str
    payment_status: str
    created_at: datetime
    items: List[OrderItem] = []
    address: Optional[Address] = None

    class Config:
        from_attributes = True

