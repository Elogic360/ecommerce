"""
Cart Schemas - Request/Response models for shopping cart operations
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# =============================================================================
# CART ITEM SCHEMAS
# =============================================================================

class CartItemBase(BaseModel):
    """Base cart item fields"""
    product_id: int
    variation_id: Optional[int] = None
    quantity: int = Field(ge=1, le=10, default=1, description="Quantity (1-10)")


class CartItemCreate(CartItemBase):
    """Schema for adding item to cart"""
    pass


class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity"""
    quantity: int = Field(ge=1, le=10, description="New quantity (1-10)")


class CartItemProductInfo(BaseModel):
    """Product info embedded in cart item response"""
    id: int
    name: str
    slug: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    primary_image: Optional[str] = None
    stock: int
    is_active: bool
    
    class Config:
        from_attributes = True


class CartItemVariationInfo(BaseModel):
    """Variation info embedded in cart item response"""
    id: int
    name: str
    value: Optional[str] = None
    price_modifier: Optional[Decimal] = None
    stock: Optional[int] = None
    
    class Config:
        from_attributes = True


class CartItemResponse(BaseModel):
    """Full cart item response with product details"""
    id: int
    cart_id: Optional[int] = None
    product_id: int
    variation_id: Optional[int] = None
    quantity: int
    unit_price: Optional[Decimal] = None
    line_total: Optional[Decimal] = None
    is_reserved: bool = False
    reserved_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Embedded product info
    product: Optional[CartItemProductInfo] = None
    variation: Optional[CartItemVariationInfo] = None
    
    # Stock status
    in_stock: bool = True
    available_quantity: int = 0
    
    class Config:
        from_attributes = True


# =============================================================================
# CART SCHEMAS
# =============================================================================

class CartBase(BaseModel):
    """Base cart fields"""
    promo_code: Optional[str] = None


class CartCreate(CartBase):
    """Schema for creating a cart"""
    session_id: Optional[str] = None  # For anonymous carts


class CartSummary(BaseModel):
    """Cart summary with totals"""
    item_count: int = 0
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    shipping_estimate: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    
    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Full cart response with items and totals"""
    id: int
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    status: str
    promo_code: Optional[str] = None
    
    # Items
    items: List[CartItemResponse] = []
    
    # Totals
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    
    # Summary
    item_count: int = 0
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    
    # Stock warnings
    has_stock_issues: bool = False
    stock_warnings: List[str] = []
    
    class Config:
        from_attributes = True


class ApplyPromoCode(BaseModel):
    """Schema for applying promo code"""
    promo_code: str = Field(min_length=3, max_length=50)


class CartMergeRequest(BaseModel):
    """Schema for merging session cart into user cart"""
    session_id: str


# =============================================================================
# SESSION CART SCHEMAS (for anonymous users)
# =============================================================================

class SessionCartCreate(BaseModel):
    """Create anonymous session cart"""
    session_id: str = Field(min_length=32, max_length=255)


class SessionCartItemAdd(BaseModel):
    """Add item to session cart"""
    session_id: str
    product_id: int
    variation_id: Optional[int] = None
    quantity: int = Field(ge=1, le=10, default=1)


# =============================================================================
# BACKWARD COMPATIBILITY - Legacy schemas
# =============================================================================

class Product(BaseModel):
    """Legacy product schema for cart items"""
    id: int
    name: str
    price: Decimal
    primary_image: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProductVariation(BaseModel):
    """Legacy variation schema"""
    id: int
    name: str
    
    class Config:
        from_attributes = True


class CartItem(CartItemBase):
    """Legacy cart item response (for backward compatibility)"""
    id: int
    user_id: Optional[int] = None
    product: Optional[Product] = None
    variation: Optional[ProductVariation] = None

    class Config:
        from_attributes = True
