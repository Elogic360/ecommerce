"""Product Models - Complete product management with categories, images, variations, and reviews."""
import re
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship  # type: ignore[attr-defined]

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customer import User
    from app.models.inventory_log import InventoryLog


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name"""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


class Product(Base):
    """Product model with comprehensive fields for e-commerce"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    short_description: Mapped[Optional[str]] = mapped_column(String(500))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    original_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    sale_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(default=0)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_featured: Mapped[bool] = mapped_column(default=False)
    is_new: Mapped[bool] = mapped_column(default=False)
    is_bestseller: Mapped[bool] = mapped_column(default=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=0)
    average_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    review_count: Mapped[int] = mapped_column(default=0)
    view_count: Mapped[int] = mapped_column(default=0)

    # Physical attributes (stored as JSON in dimensions column)
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    dimensions: Mapped[Optional[dict]] = mapped_column(Text)  # JSON: {length, width, height}

    # SEO fields
    meta_title: Mapped[Optional[str]] = mapped_column(String(255))
    meta_description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Additional fields
    tags: Mapped[Optional[dict]] = mapped_column(Text)  # JSON array of tags
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", Text)  # JSON for extra data (maps to 'metadata' column)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Images
    primary_image: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    variations: Mapped[List["ProductVariation"]] = relationship(
        "ProductVariation",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="product", cascade="all, delete-orphan"
    )
    categories: Mapped[List["Category"]] = relationship(
        "Category",
        secondary="product_category_association",
        back_populates="products",
        lazy="selectin",
    )
    inventory_logs: Mapped[List["InventoryLog"]] = relationship(
        "InventoryLog", back_populates="product"
    )
    
    # V1.5 Feature Relationships
    wishlisted_by = relationship("Wishlist", back_populates="product", cascade="all, delete-orphan")
    views = relationship("ProductView", back_populates="product", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    bundles = relationship("BundleProduct", back_populates="product")

    __table_args__ = (
        Index("ix_products_name_search", "name"),
        Index("ix_products_price_range", "price"),
        Index("ix_products_active_featured", "is_active", "is_featured"),
    )

    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0

    @property
    def is_low_stock(self) -> bool:
        return self.stock <= 10  # Default low stock threshold

    @property
    def discount_percentage(self) -> float:
        if self.original_price and self.original_price > self.price:
            return round(
                float((self.original_price - self.price) / self.original_price) * 100, 1
            )
        return 0.0


class Category(Base):
    """Category model - aligned with actual database schema"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(Text)

    # Relationship to products via association table
    products: Mapped[List["Product"]] = relationship(
        "Product",
        secondary="product_category_association",
        back_populates="categories",
    )


class ProductCategoryAssociation(Base):
    """Many-to-many association between products and categories"""

    __tablename__ = "product_category_association"
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )


class ProductImage(Base):
    """Product images with support for multiple images per product"""

    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    image_url: Mapped[str] = mapped_column(String(500))
    alt_text: Mapped[Optional[str]] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(default=False)

    product: Mapped["Product"] = relationship("Product", back_populates="images")


class ProductVariation(Base):
    """Product variations for different options (size, color, etc.)"""

    __tablename__ = "product_variations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(String(100))
    price_adjustment: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    stock: Mapped[int] = mapped_column(default=0)
    sku: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    # Note: image_url and is_active columns don't exist in DB

    product: Mapped["Product"] = relationship("Product", back_populates="variations")


class Review(Base):
    """Product reviews by customers"""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    is_verified_purchase: Mapped[bool] = mapped_column(default=False)
    is_approved: Mapped[bool] = mapped_column(default=True)
    helpful_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_check"),
        Index("ix_reviews_product_rating", "product_id", "rating"),
    )

    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    user: Mapped["User"] = relationship("User", back_populates="reviews")