"""
Order Service - Business logic for order processing and management
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus, OrderStatusHistory
from app.models.cart import Cart, CartItem, CartStatus
from app.models.product import Product, ProductVariation
from app.models.customer import User, Address
from app.models.inventory_log import InventoryLog
from app.schemas.order import (
    OrderCreate, OrderFromCart, GuestOrderCreate,
    OrderResponse, OrderListResponse, OrderSummary,
    OrderStatusUpdate, PaymentStatusUpdate
)
from app.services.cart_service import CartService


class OrderError(Exception):
    """Custom exception for order-related errors"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OrderService:
    """Service class for order operations"""
    
    # Configuration
    TAX_RATE = Decimal("0.18")  # 18% VAT
    FREE_SHIPPING_THRESHOLD = Decimal("50000")
    SHIPPING_COST = Decimal("5000")
    ORDER_CANCELLATION_WINDOW_HOURS = 24
    
    @staticmethod
    def generate_order_number() -> str:
        """Generate unique order number"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD-{timestamp}-{random_str}"
    
    @classmethod
    def create_order_from_cart(
        cls,
        db: Session,
        user: User,
        order_data: OrderFromCart
    ) -> Order:
        """
        Create order from user's cart with atomic transaction.
        
        Process:
        1. Validate cart
        2. Validate address
        3. Check stock availability
        4. Reserve stock
        5. Create order
        6. Clear cart
        7. Return order
        """
        # Get user's cart
        cart = CartService.get_cart(db, user_id=user.id)
        
        if not cart or not cart.items:
            raise OrderError("Cart is empty", status.HTTP_400_BAD_REQUEST)
        
        # Validate cart for checkout
        is_valid, issues = CartService.validate_cart_for_checkout(db, cart)
        if not is_valid:
            raise OrderError("; ".join(issues), status.HTTP_400_BAD_REQUEST)
        
        # Validate address
        address = db.query(Address).filter(
            and_(
                Address.id == order_data.address_id,
                Address.user_id == user.id
            )
        ).first()
        
        if not address:
            raise OrderError("Shipping address not found", status.HTTP_404_NOT_FOUND)
        
        try:
            # Calculate totals
            totals = cls._calculate_order_totals(db, cart.items)
            
            # Create order
            order = Order(
                user_id=user.id,
                address_id=order_data.address_id,
                order_number=cls.generate_order_number(),
                total_amount=totals["total"],
                shipping_cost=totals["shipping"],
                tax_amount=totals["tax"],
                discount_amount=totals.get("discount", Decimal("0")),
                coupon_code=order_data.promo_code,
                payment_method=order_data.payment_method,
                notes=order_data.notes,
                status=OrderStatus.PENDING.value,
                payment_status=PaymentStatus.PENDING.value,
            )
            
            db.add(order)
            db.flush()  # Get order.id
            
            # Create order items and reserve stock
            for cart_item in cart.items:
                order_item = cls._create_order_item(db, order.id, cart_item)
                db.add(order_item)
                
                # Reserve stock
                cls._reserve_stock(db, cart_item, order.id)
            
            # Record initial status
            cls._record_status_change(db, order.id, None, OrderStatus.PENDING.value, user.id)
            
            # Mark cart as converted
            CartService.mark_cart_converted(db, cart)
            
            db.commit()
            db.refresh(order)
            
            return order
            
        except Exception as e:
            db.rollback()
            raise OrderError(f"Failed to create order: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @classmethod
    def create_guest_order(
        cls,
        db: Session,
        order_data: GuestOrderCreate
    ) -> Order:
        """Create order for guest user (no auth required)"""
        
        # Validate items and calculate totals
        validated_items, totals = cls._validate_and_calculate_items(db, order_data.items)
        
        try:
            # Create order
            order = Order(
                user_id=None,  # Guest order
                address_id=None,  # Guest orders don't have address_id
                order_number=cls.generate_order_number(),
                total_amount=totals["total"],
                shipping_cost=totals["shipping"],
                tax_amount=totals["tax"],
                payment_method=order_data.payment_method,
                notes=f"Guest: {order_data.guest_name} | {order_data.guest_email} | {order_data.guest_phone}",
                status=OrderStatus.PENDING.value,
                payment_status=PaymentStatus.PENDING.value,
            )
            
            db.add(order)
            db.flush()
            
            # Create order items
            for item_data in validated_items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data["product_id"],
                    variation_id=item_data.get("variation_id"),
                    quantity=item_data["quantity"],
                    price=item_data["price"],
                )
                db.add(order_item)
                
                # Reserve stock
                cls._reserve_stock_direct(
                    db,
                    item_data["product_id"],
                    item_data["quantity"],
                    order.id
                )
            
            # Record status
            cls._record_status_change(db, order.id, None, OrderStatus.PENDING.value)
            
            db.commit()
            db.refresh(order)
            
            return order
            
        except Exception as e:
            db.rollback()
            raise OrderError(f"Failed to create guest order: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @classmethod
    def get_order(
        cls,
        db: Session,
        order_id: int,
        user_id: Optional[int] = None
    ) -> Order:
        """Get order by ID with optional user ownership check"""
        query = db.query(Order).filter(Order.id == order_id)
        
        if user_id:
            query = query.filter(Order.user_id == user_id)
        
        order = query.first()
        
        if not order:
            raise OrderError("Order not found", status.HTTP_404_NOT_FOUND)
        
        return order
    
    @classmethod
    def get_order_by_number(
        cls,
        db: Session,
        order_number: str,
        user_id: Optional[int] = None
    ) -> Order:
        """Get order by order number"""
        query = db.query(Order).filter(Order.order_number == order_number)
        
        if user_id:
            query = query.filter(Order.user_id == user_id)
        
        order = query.first()
        
        if not order:
            raise OrderError("Order not found", status.HTTP_404_NOT_FOUND)
        
        return order
    
    @classmethod
    def get_user_orders(
        cls,
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None
    ) -> OrderListResponse:
        """Get paginated list of user's orders"""
        query = db.query(Order).filter(Order.user_id == user_id)
        
        if status_filter:
            query = query.filter(Order.status == status_filter)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        orders = query.order_by(Order.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        # Build response
        total_pages = (total + page_size - 1) // page_size
        
        return OrderListResponse(
            items=[OrderSummary(
                id=o.id,
                order_number=o.order_number,
                status=o.status,
                payment_status=o.payment_status,
                total_amount=o.total_amount,
                item_count=o.item_count,
                created_at=o.created_at,
            ) for o in orders],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )
    
    @classmethod
    def update_order_status(
        cls,
        db: Session,
        order_id: int,
        new_status: str,
        admin_id: int,
        notes: Optional[str] = None
    ) -> Order:
        """Update order status (admin only)"""
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise OrderError("Order not found", status.HTTP_404_NOT_FOUND)
        
        old_status = order.status
        
        # Validate status transition
        valid_transitions = cls._get_valid_status_transitions(old_status)
        if new_status not in valid_transitions:
            raise OrderError(
                f"Cannot transition from '{old_status}' to '{new_status}'",
                status.HTTP_400_BAD_REQUEST
            )
        
        order.status = new_status
        order.admin_notes = notes if notes else order.admin_notes
        
        # Update timestamps based on status
        if new_status == OrderStatus.SHIPPED.value:
            order.shipped_at = datetime.utcnow()
        elif new_status == OrderStatus.DELIVERED.value:
            order.delivered_at = datetime.utcnow()
        
        # Record status change
        cls._record_status_change(db, order_id, old_status, new_status, admin_id, notes)
        
        db.commit()
        db.refresh(order)
        
        return order
    
    @classmethod
    def update_payment_status(
        cls,
        db: Session,
        order_id: int,
        payment_status: str,
        transaction_id: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Order:
        """Update payment status"""
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise OrderError("Order not found", status.HTTP_404_NOT_FOUND)
        
        order.payment_status = payment_status
        
        if transaction_id:
            order.payment_transaction_id = transaction_id
        
        # If payment is successful, confirm order
        if payment_status == PaymentStatus.PAID.value:
            if order.status == OrderStatus.PENDING.value:
                cls.update_order_status(db, order_id, OrderStatus.CONFIRMED.value, admin_id)
        
        db.commit()
        db.refresh(order)
        
        return order
    
    @classmethod
    def cancel_order(
        cls,
        db: Session,
        order_id: int,
        user_id: int,
        reason: Optional[str] = None,
        is_admin: bool = False
    ) -> Order:
        """Cancel order and restore stock"""
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise OrderError("Order not found", status.HTTP_404_NOT_FOUND)
        
        # Check ownership (unless admin)
        if not is_admin and order.user_id != user_id:
            raise OrderError("You can only cancel your own orders", status.HTTP_403_FORBIDDEN)
        
        # Check if cancellable
        if not order.is_cancellable:
            raise OrderError(
                f"Order with status '{order.status}' cannot be cancelled",
                status.HTTP_400_BAD_REQUEST
            )
        
        # Check cancellation window (for non-admins)
        if not is_admin:
            hours_since_order = (datetime.utcnow() - order.created_at).total_seconds() / 3600
            if hours_since_order > cls.ORDER_CANCELLATION_WINDOW_HOURS:
                raise OrderError(
                    f"Orders can only be cancelled within {cls.ORDER_CANCELLATION_WINDOW_HOURS} hours",
                    status.HTTP_400_BAD_REQUEST
                )
        
        old_status = order.status
        
        # Restore stock for each item
        for item in order.items:
            cls._release_stock(db, item.product_id, item.quantity, order.id)
        
        # Update order
        order.status = OrderStatus.CANCELLED.value
        order.cancelled_at = datetime.utcnow()
        order.cancelled_by = user_id
        order.cancellation_reason = reason
        
        # Record status change
        cls._record_status_change(db, order.id, old_status, OrderStatus.CANCELLED.value, user_id, reason)
        
        db.commit()
        db.refresh(order)
        
        return order
    
    @classmethod
    def add_tracking_info(
        cls,
        db: Session,
        order_id: int,
        tracking_number: str,
        carrier: str,
        admin_id: int
    ) -> Order:
        """Add shipping tracking information"""
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise OrderError("Order not found", status.HTTP_404_NOT_FOUND)
        
        order.tracking_number = tracking_number
        order.shipping_carrier = carrier
        
        # Update status to shipped if not already
        if order.status in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value, OrderStatus.PROCESSING.value]:
            cls.update_order_status(db, order_id, OrderStatus.SHIPPED.value, admin_id)
        
        db.commit()
        db.refresh(order)
        
        return order
    
    @classmethod
    def get_order_history(cls, db: Session, order_id: int) -> List[OrderStatusHistory]:
        """Get status history for an order"""
        return db.query(OrderStatusHistory)\
            .filter(OrderStatusHistory.order_id == order_id)\
            .order_by(OrderStatusHistory.created_at.asc())\
            .all()
    
    # =========================================================================
    # ADMIN METHODS
    # =========================================================================
    
    @classmethod
    def get_all_orders(
        cls,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        payment_status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> OrderListResponse:
        """Get all orders with filtering (admin)"""
        query = db.query(Order)
        
        if status_filter:
            query = query.filter(Order.status == status_filter)
        
        if payment_status_filter:
            query = query.filter(Order.payment_status == payment_status_filter)
        
        if search:
            query = query.filter(
                or_(
                    Order.order_number.ilike(f"%{search}%"),
                    Order.guest_email.ilike(f"%{search}%"),
                    Order.guest_name.ilike(f"%{search}%"),
                )
            )
        
        total = query.count()
        
        orders = query.order_by(Order.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        total_pages = (total + page_size - 1) // page_size
        
        return OrderListResponse(
            items=[OrderSummary(
                id=o.id,
                order_number=o.order_number,
                status=o.status,
                payment_status=o.payment_status,
                total_amount=o.total_amount,
                item_count=o.item_count,
                created_at=o.created_at,
            ) for o in orders],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    @classmethod
    def _calculate_order_totals(cls, db: Session, cart_items: List[CartItem]) -> dict:
        """Calculate order totals from cart items"""
        subtotal = Decimal("0")
        
        for item in cart_items:
            price = item.unit_price or item.product.price
            subtotal += Decimal(str(price)) * item.quantity
        
        tax = subtotal * cls.TAX_RATE
        
        shipping = Decimal("0")
        if subtotal < cls.FREE_SHIPPING_THRESHOLD:
            shipping = cls.SHIPPING_COST
        
        total = subtotal + tax + shipping
        
        return {
            "subtotal": subtotal,
            "tax": tax,
            "shipping": shipping,
            "total": total,
        }
    
    @classmethod
    def _validate_and_calculate_items(
        cls,
        db: Session,
        items: List
    ) -> Tuple[List[dict], dict]:
        """Validate items and calculate totals for direct order creation"""
        validated_items = []
        subtotal = Decimal("0")
        
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            
            if not product:
                raise OrderError(f"Product {item.product_id} not found", status.HTTP_404_NOT_FOUND)
            
            if not product.is_active:
                raise OrderError(f"Product '{product.name}' is not available", status.HTTP_400_BAD_REQUEST)
            
            if product.stock < item.quantity:
                raise OrderError(
                    f"Insufficient stock for '{product.name}'. Available: {product.stock}",
                    status.HTTP_400_BAD_REQUEST
                )
            
            item_subtotal = Decimal(str(product.price)) * item.quantity
            subtotal += item_subtotal
            
            validated_items.append({
                "product_id": product.id,
                "variation_id": item.variation_id,
                "product_name": product.name,
                "product_sku": product.sku,
                "product_image": product.primary_image,
                "quantity": item.quantity,
                "price": product.price,
                "subtotal": item_subtotal,
            })
        
        tax = subtotal * cls.TAX_RATE
        shipping = cls.SHIPPING_COST if subtotal < cls.FREE_SHIPPING_THRESHOLD else Decimal("0")
        total = subtotal + tax + shipping
        
        return validated_items, {
            "subtotal": subtotal,
            "tax": tax,
            "shipping": shipping,
            "total": total,
        }
    
    @classmethod
    def _create_order_item(cls, db: Session, order_id: int, cart_item: CartItem) -> OrderItem:
        """Create order item from cart item"""
        product = cart_item.product
        
        # Get the price to use (from cart item or product)
        item_price = cart_item.unit_price if cart_item.unit_price else product.price
        
        return OrderItem(
            order_id=order_id,
            product_id=cart_item.product_id,
            variation_id=cart_item.variation_id,
            quantity=cart_item.quantity,
            price=item_price,  # DB column is 'price' not 'unit_price'
        )
    
    @classmethod
    def _reserve_stock(cls, db: Session, cart_item: CartItem, order_id: int) -> None:
        """Reserve stock for cart item"""
        product = cart_item.product
        
        if product.stock < cart_item.quantity:
            raise OrderError(
                f"Insufficient stock for '{product.name}'",
                status.HTTP_400_BAD_REQUEST
            )
        
        product.stock -= cart_item.quantity
        
        # Log inventory change
        log = InventoryLog(
            product_id=product.id,
            change_quantity=-cart_item.quantity,
            new_stock=product.stock,
            reason="order_placed",
            order_id=order_id,
        )
        db.add(log)
    
    @classmethod
    def _reserve_stock_direct(cls, db: Session, product_id: int, quantity: int, order_id: int) -> None:
        """Reserve stock directly by product ID"""
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise OrderError(f"Product {product_id} not found", status.HTTP_404_NOT_FOUND)
        
        if product.stock < quantity:
            raise OrderError(
                f"Insufficient stock for '{product.name}'",
                status.HTTP_400_BAD_REQUEST
            )
        
        product.stock -= quantity
        
        log = InventoryLog(
            product_id=product.id,
            change_quantity=-quantity,
            new_stock=product.stock,
            reason="order_placed",
            order_id=order_id,
        )
        db.add(log)
    
    @classmethod
    def _release_stock(cls, db: Session, product_id: int, quantity: int, order_id: int) -> None:
        """Release reserved stock (for cancellations)"""
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if product:
            product.stock += quantity
            
            log = InventoryLog(
                product_id=product.id,
                change_quantity=quantity,
                new_stock=product.stock,
                reason="order_cancelled",
                order_id=order_id,
            )
            db.add(log)
    
    @classmethod
    def _record_status_change(
        cls,
        db: Session,
        order_id: int,
        from_status: Optional[str],
        to_status: str,
        changed_by: Optional[int] = None,
        notes: Optional[str] = None
    ) -> None:
        """Record order status change in history"""
        history = OrderStatusHistory(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            notes=notes,
        )
        db.add(history)
    
    @staticmethod
    def _get_valid_status_transitions(current_status: str) -> List[str]:
        """Get valid status transitions from current status"""
        transitions = {
            OrderStatus.PENDING.value: [
                OrderStatus.CONFIRMED.value,
                OrderStatus.CANCELLED.value,
                OrderStatus.FAILED.value,
                OrderStatus.ON_HOLD.value,
            ],
            OrderStatus.CONFIRMED.value: [
                OrderStatus.PROCESSING.value,
                OrderStatus.CANCELLED.value,
                OrderStatus.ON_HOLD.value,
            ],
            OrderStatus.PROCESSING.value: [
                OrderStatus.SHIPPED.value,
                OrderStatus.CANCELLED.value,
                OrderStatus.ON_HOLD.value,
            ],
            OrderStatus.SHIPPED.value: [
                OrderStatus.OUT_FOR_DELIVERY.value,
                OrderStatus.DELIVERED.value,
            ],
            OrderStatus.OUT_FOR_DELIVERY.value: [
                OrderStatus.DELIVERED.value,
            ],
            OrderStatus.DELIVERED.value: [
                OrderStatus.REFUNDED.value,
            ],
            OrderStatus.ON_HOLD.value: [
                OrderStatus.PENDING.value,
                OrderStatus.PROCESSING.value,
                OrderStatus.CANCELLED.value,
            ],
            OrderStatus.CANCELLED.value: [],  # Terminal state
            OrderStatus.REFUNDED.value: [],  # Terminal state
            OrderStatus.FAILED.value: [
                OrderStatus.PENDING.value,  # Can retry
            ],
        }
        return transitions.get(current_status, [])


# =============================================================================
# EMAIL NOTIFICATION PREPARATION (to be implemented)
# =============================================================================

class OrderNotificationService:
    """
    Email notification service for orders.
    TODO: Implement with actual email provider (SendGrid, SES, etc.)
    """
    
    @staticmethod
    def send_order_confirmation(order: Order) -> bool:
        """Send order confirmation email"""
        # TODO: Implement email sending
        # email_to = order.guest_email if order.guest_email else order.user.email
        # template = "order_confirmation"
        # context = {"order": order, "items": order.items}
        return True
    
    @staticmethod
    def send_shipping_notification(order: Order) -> bool:
        """Send shipping notification with tracking"""
        # TODO: Implement
        return True
    
    @staticmethod
    def send_delivery_confirmation(order: Order) -> bool:
        """Send delivery confirmation"""
        # TODO: Implement
        return True
    
    @staticmethod
    def send_cancellation_confirmation(order: Order) -> bool:
        """Send cancellation confirmation"""
        # TODO: Implement
        return True

