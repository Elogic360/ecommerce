"""
Cart Models - Shopping cart with session and user-based support
"""
import enum
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship  # type: ignore[attr-defined]

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customer import User
    from app.models.product import Product, ProductVariation


class CartStatus(str, enum.Enum):
    """Cart status for tracking cart lifecycle"""

    ACTIVE = "active"
    CONVERTED = "converted"  # Converted to order
    EXPIRED = "expired"
    ABANDONED = "abandoned"


class Cart(Base):
    """
    Cart model for grouping cart items.
    Supports both authenticated users and anonymous sessions.
    """

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # User association (NULL for anonymous carts)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # Session ID for anonymous users
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, unique=True)

    # Cart status
    status: Mapped[str] = mapped_column(String(20), default=CartStatus.ACTIVE.value)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Cached totals
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Promo code
    promo_code: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="cart")
    items: Mapped[List["CartItem"]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan", lazy="selectin"
    )

    # Indexes
    __table_args__ = (
        Index("ix_carts_user_active", "user_id", "status"),
        Index("ix_carts_session_active", "session_id", "status"),
        Index("ix_carts_expires", "expires_at"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if cart has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def item_count(self) -> int:
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items) if self.items else 0

    def set_expiration(self, hours: int = 72):
        """Set cart expiration time"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)

    def refresh_expiration(self, hours: int = 72):
        """Refresh cart expiration on activity"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.updated_at = datetime.utcnow()


class CartItem(Base):
    """
    Cart item model with stock validation support.
    """

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Cart association
    cart_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("carts.id", ondelete="CASCADE"), index=True
    )

    # Legacy user_id
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )

    # Product reference
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    variation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("product_variations.id", ondelete="SET NULL")
    )

    # Quantity
    quantity: Mapped[int] = mapped_column(default=1)

    # Price snapshot
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    # For reserved items during checkout
    is_reserved: Mapped[bool] = mapped_column(default=False)
    reserved_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="cart_items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    variation: Mapped[Optional["ProductVariation"]] = relationship(
        "ProductVariation", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_cart_items_cart_product", "cart_id", "product_id", "variation_id"),
    )

    @property
    def line_total(self) -> float:
        """Calculate line total for this item"""
        price = (
            float(self.unit_price)
            if self.unit_price
            else (float(self.product.price) if self.product else 0)
        )
        return price * self.quantity
