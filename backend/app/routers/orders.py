"""
Order Router - Order management endpoints
Supports order creation, history, status updates, and admin management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import EmailStr

from app.db.session import get_db
from app.models.customer import User
from app.models.order import OrderStatus, PaymentStatus
from app.core.security import get_current_user, get_current_admin_user
from app.schemas.order import (
    OrderCreate, OrderFromCart, GuestOrderCreate,
    OrderResponse, OrderListResponse, OrderSummary,
    OrderStatusUpdate, PaymentStatusUpdate, ShippingUpdate,
    CancelOrderRequest, OrderStatusHistoryResponse,
    Order as OrderSchema
)
from app.services.orders import OrderService, OrderError

router = APIRouter(prefix="/orders", tags=["Orders"])


# =============================================================================
# USER ORDER ENDPOINTS
# =============================================================================

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderFromCart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create order from user's cart.
    
    Process:
    1. Validates cart items and stock
    2. Reserves stock
    3. Creates order with items
    4. Clears cart
    5. Returns order details
    """
    try:
        order = OrderService.create_order_from_cart(db, current_user, order_data)
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/direct", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_direct_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create order with items directly (bypass cart).
    Useful for one-click purchases or API integrations.
    """
    try:
        # Build cart-like structure and use same flow
        from app.services.cart_service import CartService
        from app.schemas.cart import CartItemCreate
        
        cart = CartService.get_or_create_cart(db, user_id=current_user.id)
        
        # Clear existing cart and add new items
        CartService.clear_cart(db, cart)
        
        for item in order_data.items:
            CartService.add_item(db, cart, CartItemCreate(
                product_id=item.product_id,
                variation_id=item.variation_id,
                quantity=item.quantity
            ))
        
        # Create order from cart
        from app.schemas.order import OrderFromCart
        order_from_cart = OrderFromCart(
            address_id=order_data.address_id,
            payment_method=order_data.payment_method,
            notes=order_data.notes,
        )
        
        order = OrderService.create_order_from_cart(db, current_user, order_from_cart)
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("", response_model=OrderListResponse)
def get_user_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's order history with pagination"""
    return OrderService.get_user_orders(
        db, current_user.id, page, page_size, status_filter
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific order details (user must own the order)"""
    try:
        order = OrderService.get_order(db, order_id, user_id=current_user.id)
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/number/{order_number}", response_model=OrderResponse)
def get_order_by_number(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get order by order number"""
    try:
        order = OrderService.get_order_by_number(db, order_number, user_id=current_user.id)
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    cancel_request: Optional[CancelOrderRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel order (user-initiated).
    
    - Can only cancel within 24 hours of order creation
    - Can only cancel orders in pending/confirmed/processing status
    - Stock is automatically restored
    """
    reason = cancel_request.reason if cancel_request else None
    
    try:
        order = OrderService.cancel_order(
            db, order_id, current_user.id, reason, is_admin=False
        )
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/{order_id}/history", response_model=list)
def get_order_history(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get order status history"""
    # Verify ownership
    try:
        OrderService.get_order(db, order_id, user_id=current_user.id)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
    history = OrderService.get_order_history(db, order_id)
    return [OrderStatusHistoryResponse.model_validate(h) for h in history]


# =============================================================================
# GUEST ORDER ENDPOINTS
# =============================================================================

@router.post("/guest", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_guest_order(
    order_data: GuestOrderCreate,
    db: Session = Depends(get_db)
):
    """
    Create order for guest user (no authentication required).
    
    Guest provides:
    - Email, name, phone
    - Shipping address
    - Order items
    - Payment method
    """
    try:
        order = OrderService.create_guest_order(db, order_data)
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "total_amount": float(order.total_amount),
            "status": order.status,
            "clear_client_cart": True,
            "message": "Order created successfully. Confirmation will be sent to your email.",
            "tracking_email": order.guest_email,
        }
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/guest/track")
def track_guest_order(
    order_number: str = Query(...),
    email: EmailStr = Query(...),
    db: Session = Depends(get_db)
):
    """
    Track guest order by order number and email.
    Returns order status and details.
    """
    try:
        order = OrderService.get_order_by_number(db, order_number)
        
        # Verify email matches
        if order.guest_email != email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email does not match order"
            )
        
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# ADMIN ORDER ENDPOINTS
# =============================================================================

@router.get("/admin/all", response_model=OrderListResponse)
def get_all_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    payment_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Get all orders with filtering (admin only).
    
    Filters:
    - status_filter: Order status
    - payment_status: Payment status
    - search: Search by order number, email, or name
    """
    return OrderService.get_all_orders(
        db, page, page_size, status_filter, payment_status, search
    )


@router.get("/admin/{order_id}", response_model=OrderResponse)
def admin_get_order(
    order_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Get any order details (admin only)"""
    try:
        order = OrderService.get_order(db, order_id)  # No user_id filter
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/admin/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Update order status (admin only).
    
    Valid status transitions:
    - pending → confirmed, cancelled, failed, on_hold
    - confirmed → processing, cancelled, on_hold
    - processing → shipped, cancelled, on_hold
    - shipped → out_for_delivery, delivered
    - out_for_delivery → delivered
    - delivered → refunded
    """
    try:
        order = OrderService.update_order_status(
            db, order_id, status_update.status.value, admin_user.id, status_update.notes
        )
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/admin/{order_id}/payment", response_model=OrderResponse)
def update_payment_status(
    order_id: int,
    payment_update: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Update payment status (admin only)"""
    try:
        order = OrderService.update_payment_status(
            db, order_id, payment_update.payment_status.value,
            payment_update.transaction_id, admin_user.id
        )
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/admin/{order_id}/shipping", response_model=OrderResponse)
def update_shipping_info(
    order_id: int,
    shipping_update: ShippingUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Add/update shipping tracking information (admin only)"""
    try:
        order = OrderService.add_tracking_info(
            db, order_id,
            shipping_update.tracking_number,
            shipping_update.shipping_carrier,
            admin_user.id
        )
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/admin/{order_id}/cancel", response_model=OrderResponse)
def admin_cancel_order(
    order_id: int,
    cancel_request: Optional[CancelOrderRequest] = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Cancel any order (admin only, no time restriction)"""
    reason = cancel_request.reason if cancel_request else None
    
    try:
        order = OrderService.cancel_order(
            db, order_id, admin_user.id, reason, is_admin=True
        )
        return _build_order_response(order)
    except OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# ORDER STATUS REFERENCE
# =============================================================================

@router.get("/meta/statuses")
def get_order_statuses():
    """Get all available order statuses"""
    return {
        "order_statuses": [s.value for s in OrderStatus],
        "payment_statuses": [s.value for s in PaymentStatus],
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _build_order_response(order) -> OrderResponse:
    """Build OrderResponse from Order model"""
    from app.schemas.order import OrderItemResponse, OrderItemProductInfo, Address
    
    items = []
    for item in order.items:
        product_info = None
        if item.product:
            product_info = OrderItemProductInfo(
                id=item.product.id,
                name=item.product.name,
                slug=item.product.slug,
                sku=item.product.sku,
                primary_image=item.product.primary_image,
            )
        
        items.append(OrderItemResponse(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            variation_id=item.variation_id,
            product_name=item.product_name,
            product_sku=item.product_sku,
            product_image=item.product_image,
            quantity=item.quantity,
            unit_price=item.unit_price,
            original_price=item.original_price,
            discount=item.discount or 0,
            subtotal=item.subtotal,
            tax=item.tax,
            total=item.total,
            status=item.status,
            product=product_info,
        ))
    
    address_response = None
    if order.address:
        address_response = Address(
            id=order.address.id,
            user_id=order.address.user_id,
            label=order.address.label,
            address_line_1=order.address.address_line_1,
            address_line_2=order.address.address_line_2,
            city=order.address.city,
            state=order.address.state,
            postal_code=order.address.postal_code,
            country=order.address.country,
            contact_name=order.address.contact_name,
            contact_phone=order.address.contact_phone,
            is_default=order.address.is_default,
        )
    
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        user_id=order.user_id,
        status=order.status,
        payment_status=order.payment_status,
        subtotal=order.subtotal,
        total_amount=order.total_amount,
        shipping_cost=order.shipping_cost,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount or 0,
        promo_code=order.promo_code,
        payment_method=order.payment_method,
        payment_transaction_id=order.payment_transaction_id,
        payment_gateway=order.payment_gateway,
        tracking_number=order.tracking_number,
        shipping_carrier=order.shipping_carrier,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        guest_email=order.guest_email,
        guest_name=order.guest_name,
        guest_phone=order.guest_phone,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
        address=address_response,
        item_count=order.item_count,
        is_cancellable=order.is_cancellable,
        clear_client_cart=True,
    )

