from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship  # type: ignore[attr-defined]

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customer import User
    from app.models.product import Product
    from app.models.order import Order


class InventoryLog(Base):
    """
    Tracks all inventory changes for audit trail
    Records stock adjustments, sales, returns, and manual corrections
    """

    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), index=True
    )
    change_quantity: Mapped[int] = mapped_column(Integer)
    new_stock: Mapped[Optional[int]] = mapped_column(
        Integer, CheckConstraint("new_stock >= 0")
    )
    reason: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # References
    admin_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("orders.id"), index=True
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="inventory_logs")
    admin: Mapped[Optional["User"]] = relationship("User", foreign_keys=[admin_id])
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="inventory_logs")

    def __repr__(self) -> str:
        return f"<InventoryLog(id={self.id}, product_id={self.product_id}, change={self.change_quantity}, new_stock={self.new_stock})>"