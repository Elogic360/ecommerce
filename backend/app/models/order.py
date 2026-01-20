"""
Order Models - Order management with status tracking and payment integration
"""
import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
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
    from app.models.customer import User, Address
    from app.models.product import Product, ProductVariation
    from app.models.inventory_log import InventoryLog
    from app.models.features import CouponUsage, ReturnRequest


class OrderStatus(str, enum.Enum):
    """Order status workflow"""

    PENDING = "pending"  # Order created, awaiting payment
    CONFIRMED = "confirmed"  # Payment received, order confirmed
    PROCESSING = "processing"  # Order is being prepared
    SHIPPED = "shipped"  # Order has been shipped
    OUT_FOR_DELIVERY = "out_for_delivery"  # With delivery carrier
    DELIVERED = "delivered"  # Order delivered to customer
    CANCELLED = "cancelled"  # Order cancelled
    REFUNDED = "refunded"  # Order refunded
    ON_HOLD = "on_hold"  # Order on hold (stock issue, etc.)
    FAILED = "failed"  # Order failed (payment failed, etc.)


class PaymentStatus(str, enum.Enum):
    """Payment status tracking"""

    PENDING = "pending"  # Awaiting payment
    PROCESSING = "processing"  # Payment is being processed
    PAID = "paid"  # Payment successful
    FAILED = "failed"  # Payment failed
    REFUNDED = "refunded"  # Payment refunded
    PARTIALLY_REFUNDED = "partially_refunded"  # Partial refund
    CANCELLED = "cancelled"  # Payment cancelled


class PaymentMethod(str, enum.Enum):
    """Supported payment methods"""

    CASH_ON_DELIVERY = "cod"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"


class Order(Base):
    """
    Order model - aligned with actual database schema.
    Database columns: id, user_id, address_id, order_number, total_amount, shipping_cost,
    tax_amount, payment_method, payment_status, status, notes, created_at, updated_at,
    tracking_number, carrier, estimated_delivery, coupon_code, discount_amount,
    loyalty_points_earned, loyalty_points_used
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # User association (NULL for guest orders)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    # Shipping address
    address_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("addresses.id", ondelete="SET NULL")
    )

    # Order identification
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # Order amounts (DB has: total_amount, shipping_cost, tax_amount, discount_amount)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.0)

    # Payment information
    payment_method: Mapped[str] = mapped_column(
        String(50), default=PaymentMethod.CASH_ON_DELIVERY.value
    )
    payment_status: Mapped[str] = mapped_column(
        String(30), default=PaymentStatus.PENDING.value, index=True
    )

    # Order status
    status: Mapped[str] = mapped_column(String(30), default=OrderStatus.PENDING.value, index=True)

    # Shipping tracking (DB uses 'carrier' not 'shipping_carrier')
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100))
    carrier: Mapped[Optional[str]] = mapped_column(String(100))
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Coupon/discount
    coupon_code: Mapped[Optional[str]] = mapped_column(String(50))

    # Loyalty points
    loyalty_points_earned: Mapped[int] = mapped_column(Integer, default=0)
    loyalty_points_used: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="orders")
    address: Mapped[Optional["Address"]] = relationship("Address")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    inventory_logs: Mapped[List["InventoryLog"]] = relationship(
        "InventoryLog", back_populates="order", lazy="selectin"
    )
    coupon_usage: Mapped[List["CouponUsage"]] = relationship(
        "CouponUsage", back_populates="order", lazy="selectin"
    )
    return_requests: Mapped[List["ReturnRequest"]] = relationship(
        "ReturnRequest", back_populates="order", lazy="selectin"
    )

    # Computed properties for backwards compatibility
    @property
    def guest_name(self) -> Optional[str]:
        """Guest name from user or None"""
        return self.user.full_name if self.user else None

    @property
    def guest_email(self) -> Optional[str]:
        """Guest email from user or None"""
        return self.user.email if self.user else None

    @property
    def guest_phone(self) -> Optional[str]:
        """Guest phone - not in DB"""
        return None

    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal from items or use total_amount"""
        if self.items:
            return sum(item.price * item.quantity for item in self.items)
        return self.total_amount - self.shipping_cost - self.tax_amount + self.discount_amount

    @property
    def is_cancellable(self) -> bool:
        """Check if order can be cancelled"""
        return self.status in [
            OrderStatus.PENDING.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.PROCESSING.value,
        ]

    @property
    def is_paid(self) -> bool:
        """Check if order is paid"""
        return self.payment_status == PaymentStatus.PAID.value

    @property
    def item_count(self) -> int:
        """Get total number of items in order"""
        return sum(item.quantity for item in self.items) if self.items else 0

    @property
    def promo_code(self) -> Optional[str]:
        """Alias for coupon_code for backwards compatibility"""
        return self.coupon_code

    @property
    def payment_transaction_id(self) -> Optional[str]:
        """Payment transaction ID - not stored"""
        return None

    @property
    def payment_gateway(self) -> Optional[str]:
        """Payment gateway - not stored"""
        return None

    @property
    def shipping_carrier(self) -> Optional[str]:
        """Alias for carrier for backwards compatibility"""
        return self.carrier

    @property
    def shipped_at(self) -> Optional[datetime]:
        """Shipped date - not stored separately"""
        return None

    @property
    def delivered_at(self) -> Optional[datetime]:
        """Delivered date - not stored separately"""
        return None


class OrderItem(Base):
    """
    Order line item - aligned with actual database schema.
    Database columns: id, order_id, product_id, variation_id, quantity, price
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="SET NULL")
    )
    variation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("product_variations.id", ondelete="SET NULL")
    )

    # Quantity and price (DB uses 'price' not 'unit_price')
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="selectin")
    variation: Mapped[Optional["ProductVariation"]] = relationship(
        "ProductVariation", lazy="selectin"
    )

    # Computed properties for backwards compatibility
    @property
    def unit_price(self) -> Decimal:
        """Alias for price for backwards compatibility"""
        return self.price

    @property
    def product_name(self) -> Optional[str]:
        """Get product name from relationship"""
        return self.product.name if self.product else None

    @property
    def product_sku(self) -> Optional[str]:
        """Get product SKU from relationship"""
        return self.product.sku if self.product else None

    @property
    def product_image(self) -> Optional[str]:
        """Get product image from relationship"""
        return self.product.primary_image if self.product else None

    @property
    def original_price(self) -> Optional[Decimal]:
        """Get original price from product"""
        return self.product.original_price if self.product else None

    @property
    def discount(self) -> Decimal:
        """Calculate discount (not stored in DB)"""
        return Decimal("0")

    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal"""
        return self.price * self.quantity

    @property
    def tax(self) -> Decimal:
        """Tax amount (not stored per-item)"""
        return Decimal("0")

    @property
    def total(self) -> Decimal:
        """Calculate total"""
        return self.price * self.quantity

    @property
    def status(self) -> str:
        """Item status (not stored, use order status)"""
        return "confirmed"

    @property
    def line_total(self) -> float:
        """Calculate line total"""
        return float(self.price * self.quantity)


class OrderStatusHistory(Base):
    """Track order status changes for audit trail"""

    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )

    # Status change
    from_status: Mapped[Optional[str]] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))

    # Who made the change
    changed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )

    # Additional info
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    user: Mapped[Optional["User"]] = relationship("User")