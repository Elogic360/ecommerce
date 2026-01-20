"""Product Schemas - Pydantic models for product management API."""
from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import re


# =============================================================================
# PRODUCT IMAGE SCHEMAS
# =============================================================================

class ProductImageBase(BaseModel):
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool = False


class ProductImageCreate(BaseModel):
    alt_text: Optional[str] = None
    is_primary: bool = False


class ProductImage(ProductImageBase):
    id: int
    product_id: int
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# PRODUCT VARIATION SCHEMAS
# =============================================================================

class ProductVariationBase(BaseModel):
    """ProductVariation base - aligned with actual database schema
    Database columns: id, product_id, name, value, price_adjustment, stock, sku (only 7 columns)
    """
    name: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=100)
    price_adjustment: Decimal = Decimal("0.00")
    stock: int = Field(default=0, ge=0)
    sku: Optional[str] = Field(None, max_length=100)


class ProductVariationCreate(ProductVariationBase):
    pass


class ProductVariationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[str] = Field(None, min_length=1, max_length=100)
    price_adjustment: Optional[Decimal] = None
    stock: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, max_length=100)


class ProductVariation(ProductVariationBase):
    id: int
    product_id: int
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# CATEGORY SCHEMAS
# =============================================================================

class CategoryBase(BaseModel):
    """Category base - aligned with actual database schema (id, name, description, image_url only)"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None


class CategoryCreate(CategoryBase):
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Category name cannot be empty')
        return v.strip()


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None


class CategorySimple(BaseModel):
    """Simplified category for product listings"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)


class Category(CategoryBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class CategoryWithChildren(Category):
    """Category with nested children for hierarchical display"""
    children: List['CategoryWithChildren'] = []
    product_count: int = 0


# =============================================================================
# REVIEW SCHEMAS
# =============================================================================

class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = None


class ReviewUser(BaseModel):
    """Simplified user info for reviews"""
    id: int
    username: str
    full_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class Review(ReviewBase):
    id: int
    product_id: int
    user_id: int
    is_verified_purchase: bool = False
    helpful_count: int = 0
    created_at: Optional[datetime] = None
    user: Optional[ReviewUser] = None
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# PRODUCT SCHEMAS
# =============================================================================

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    original_price: Optional[Decimal] = Field(None, ge=0)
    sale_price: Optional[Decimal] = Field(None, ge=0)
    stock: int = Field(default=0, ge=0)
    sku: str = Field(..., min_length=1, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    is_featured: bool = False
    is_new: bool = False
    is_bestseller: bool = False
    
    # Physical attributes
    weight: Optional[Decimal] = Field(None, ge=0)
    dimensions: Optional[dict] = None  # JSON: {length, width, height}
    
    # SEO
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None
    
    # Additional
    tags: Optional[List[str]] = None
    extra_data: Optional[dict] = None


class ProductCreate(ProductBase):
    category_ids: List[int] = []
    variations: List[ProductVariationCreate] = []
    
    @validator('sku')
    def validate_sku(cls, v):
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError('SKU can only contain letters, numbers, underscores, and hyphens')
        return v.upper()
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Product name cannot be empty')
        return v.strip()


class ProductCreateSimple(BaseModel):
    """Simplified product creation - just the essentials"""
    name: str = Field(..., min_length=1, max_length=255)
    category_id: Optional[int] = None  # Optional category
    price: Decimal = Field(..., gt=0, decimal_places=2)
    new_price: Optional[Decimal] = Field(None, gt=0)  # For discounts/price changes
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Product name cannot be empty')
        return v.strip()


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    price: Optional[Decimal] = Field(None, gt=0)
    original_price: Optional[Decimal] = Field(None, ge=0)
    sale_price: Optional[Decimal] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_new: Optional[bool] = None
    is_bestseller: Optional[bool] = None
    weight: Optional[Decimal] = Field(None, ge=0)
    dimensions: Optional[dict] = None
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None
    tags: Optional[List[str]] = None
    extra_data: Optional[dict] = None
    category_ids: Optional[List[int]] = None


class ProductSimple(BaseModel):
    """Simplified product for listings"""
    id: int
    name: str
    slug: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    stock: int = 0  # Add stock field for frontend
    primary_image: Optional[str] = None
    rating: Decimal = Decimal("0")
    average_rating: Decimal = Decimal("0")
    review_count: int = 0
    is_in_stock: bool = True
    is_featured: bool = False
    is_new: bool = False
    is_bestseller: bool = False
    brand: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class Product(ProductBase):
    id: int
    slug: Optional[str] = None
    rating: Decimal = Decimal("0")
    average_rating: Decimal = Decimal("0")
    review_count: int = 0
    view_count: int = 0
    primary_image: Optional[str] = None
    images: List[ProductImage] = []
    variations: List[ProductVariation] = []
    categories: List[CategorySimple] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Computed properties
    is_in_stock: bool = True
    is_low_stock: bool = False
    discount_percentage: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)
    
    @validator('is_in_stock', pre=True, always=True)
    def compute_in_stock(cls, v, values):
        stock = values.get('stock', 0)
        return stock > 0 if isinstance(stock, int) else v
    
    @validator('is_low_stock', pre=True, always=True)
    def compute_low_stock(cls, v, values):
        stock = values.get('stock', 0)
        return stock <= 10 if isinstance(stock, int) else v
    
    @validator('discount_percentage', pre=True, always=True)
    def compute_discount(cls, v, values):
        price = values.get('price')
        original = values.get('original_price')
        if original and price and original > price:
            return round(float((original - price) / original) * 100, 1)
        return 0.0


class ProductDetail(Product):
    """Full product detail with reviews"""
    recent_reviews: List[Review] = []


# =============================================================================
# PAGINATION SCHEMAS
# =============================================================================

class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ProductListResponse(BaseModel):
    """Paginated product list response"""
    items: List[ProductSimple]
    meta: PaginationMeta


class CategoryListResponse(BaseModel):
    """Category list response with product counts"""
    items: List[Category]
    total: int


# =============================================================================
# FILTER SCHEMAS
# =============================================================================

class ProductFilter(BaseModel):
    """Product search and filter parameters"""
    search: Optional[str] = None
    category_id: Optional[int] = None
    category_ids: Optional[List[int]] = None
    brand: Optional[str] = None
    brands: Optional[List[str]] = None
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = True
    in_stock: Optional[bool] = None
    min_rating: Optional[Decimal] = Field(None, ge=0, le=5)
    sort_by: str = Field(default="created_at", pattern="^(price|rating|created_at|name|view_count)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class StockUpdateRequest(BaseModel):
    """Stock update request"""
    quantity: int = Field(..., description="Positive to add, negative to subtract")
    reason: Optional[str] = Field(None, max_length=255)


class BulkStockUpdate(BaseModel):
    """Bulk stock update for multiple products"""
    updates: List[dict]  # [{product_id: int, quantity: int, reason: str}]