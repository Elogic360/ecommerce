import enum
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship  # type: ignore[attr-defined]

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.product import Review
    from app.models.cart import Cart, CartItem


class Role(str, enum.Enum):
    """User roles for role-based access control (RBAC)"""

    ADMIN = "admin"
    INVENTORY_MANAGER = "inventory_manager"
    SALES_ADMIN = "sales_admin"
    ORDER_VERIFIER = "order_verifier"
    TRANSPORTER = "transporter"
    USER = "user"

    @classmethod
    def get_admin_roles(cls) -> list["Role"]:
        """Roles with administrative privileges"""
        return [cls.ADMIN, cls.INVENTORY_MANAGER, cls.SALES_ADMIN]

    @classmethod
    def get_staff_roles(cls) -> list["Role"]:
        """All staff roles (non-customer)"""
        return [
            cls.ADMIN,
            cls.INVENTORY_MANAGER,
            cls.SALES_ADMIN,
            cls.ORDER_VERIFIER,
            cls.TRANSPORTER,
        ]


class User(Base):
    """
    User model for authentication and authorization.
    Supports multiple roles for RBAC.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(Text)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Role-based access control
    role: Mapped[Optional[str]] = mapped_column(String(50), default=Role.USER.value)

    # Loyalty program
    loyalty_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    loyalty_points: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    # User activity tracking
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    preferred_currency: Mapped[Optional[str]] = mapped_column(String(3), default="USD")
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Timestamps
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    addresses: Mapped[List["Address"]] = relationship(
        "Address", back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order", foreign_keys="Order.user_id", back_populates="user"
    )
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="user")
    cart_items: Mapped[List["CartItem"]] = relationship(
        "CartItem", back_populates="user", cascade="all, delete-orphan"
    )
    cart: Mapped[Optional["Cart"]] = relationship(
        "Cart", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    
    # V1.5 Feature Relationships
    wishlists = relationship("Wishlist", back_populates="user", cascade="all, delete-orphan")
    coupon_usages = relationship("CouponUsage", back_populates="user", cascade="all, delete-orphan")
    loyalty_transactions = relationship("LoyaltyPoint", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    product_views = relationship("ProductView", back_populates="user")
    abandoned_carts = relationship("AbandonedCart", back_populates="user", cascade="all, delete-orphan")
    return_requests = relationship("ReturnRequest", back_populates="user", foreign_keys="ReturnRequest.user_id")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == Role.ADMIN.value

    @property
    def is_staff(self) -> bool:
        """Check if user is any staff member"""
        return self.role in [r.value for r in Role.get_staff_roles()]

    def has_role(self, role: Role) -> bool:
        """Check if user has a specific role"""
        return self.role == role.value

    def has_any_role(self, roles: list[Role]) -> bool:
        """Check if user has any of the specified roles"""
        return self.role in [r.value for r in roles]

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token for password reset or email verification"""
        return secrets.token_urlsafe(32)


class Address(Base):
    """User shipping/billing address"""

    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address_line_1: Mapped[str] = mapped_column(String(255))
    address_line_2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="addresses")
    
    # =========================================================================
    # COMPATIBILITY PROPERTIES for columns that don't exist in DB
    # =========================================================================
    
    @property
    def is_billing(self) -> bool:
        """Compatibility: is_billing doesn't exist in DB"""
        return False
    
    @property
    def is_shipping(self) -> bool:
        """Compatibility: is_shipping doesn't exist in DB"""
        return True
    
    @property
    def contact_name(self) -> Optional[str]:
        """Compatibility: contact_name doesn't exist in DB"""
        return None
    
    @property
    def contact_phone(self) -> Optional[str]:
        """Compatibility: contact_phone doesn't exist in DB"""
        return None
    
    @property
    def updated_at(self) -> Optional[datetime]:
        """Compatibility: updated_at doesn't exist in DB"""
        return None