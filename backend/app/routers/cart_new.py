"""
Cart Router - Shopping cart management endpoints
Supports both authenticated users and anonymous session carts.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Cookie
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.cart import (
    CartItemCreate, CartItemUpdate, CartResponse, CartItemResponse,
    CartSummary, ApplyPromoCode, CartMergeRequest
)
from app.models.cart import Cart, CartItem as CartItemModel
from app.models.customer import User
from app.core.security import get_current_user, get_current_user_optional
from app.services.cart_service import CartService, CartError

router = APIRouter(prefix="/cart", tags=["Cart"])


# =============================================================================
# CART ENDPOINTS (Authenticated Users)
# =============================================================================

@router.get("", response_model=CartResponse)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's cart with items and totals.
    Creates a new cart if one doesn't exist.
    """
    cart = CartService.get_or_create_cart(db, user_id=current_user.id)
    
    # Validate cart and get warnings
    is_valid, issues = CartService.validate_cart_for_checkout(db, cart)
    
    return _build_cart_response(cart, not is_valid, issues)


@router.get("/summary", response_model=CartSummary)
def get_cart_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get cart summary with totals"""
    cart = CartService.get_cart(db, user_id=current_user.id)
    
    if not cart:
        return CartSummary()
    
    return CartService.get_cart_summary(db, cart)


@router.post("/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    item: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add item to cart.
    - Maximum quantity per item: 10
    - Validates stock availability
    - If item already exists, quantity is added
    """
    cart = CartService.get_or_create_cart(db, user_id=current_user.id)
    
    try:
        cart_item = CartService.add_item(db, cart, item)
        return _build_cart_item_response(cart_item)
    except CartError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/items/{item_id}", response_model=CartItemResponse)
def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update cart item quantity.
    - Maximum quantity: 10
    - Validates stock availability
    """
    cart = CartService.get_cart(db, user_id=current_user.id)
    
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    
    try:
        cart_item = CartService.update_item_quantity(db, cart, item_id, item_update.quantity)
        return _build_cart_item_response(cart_item)
    except CartError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/items/{item_id}")
def remove_from_cart(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove item from cart"""
    cart = CartService.get_cart(db, user_id=current_user.id)
    
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    
    try:
        CartService.remove_item(db, cart, item_id)
        return {"message": "Item removed from cart"}
    except CartError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("")
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear all items from cart"""
    cart = CartService.get_cart(db, user_id=current_user.id)
    
    if cart:
        CartService.clear_cart(db, cart)
    
    return {"message": "Cart cleared successfully"}


@router.post("/promo-code")
def apply_promo_code(
    promo: ApplyPromoCode,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Apply promo code to cart"""
    cart = CartService.get_cart(db, user_id=current_user.id)
    
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    
    success, message = CartService.apply_promo_code(db, cart, promo.promo_code)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {"message": message}


@router.delete("/promo-code")
def remove_promo_code(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove promo code from cart"""
    cart = CartService.get_cart(db, user_id=current_user.id)
    
    if cart:
        cart.promo_code = None
        cart.discount_amount = 0
        db.commit()
    
    return {"message": "Promo code removed"}


@router.post("/validate")
def validate_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate cart for checkout.
    Returns list of issues if any items have stock problems.
    """
    cart = CartService.get_cart(db, user_id=current_user.id)
    
    if not cart or not cart.items:
        return {"valid": False, "issues": ["Cart is empty"]}
    
    is_valid, issues = CartService.validate_cart_for_checkout(db, cart)
    
    return {"valid": is_valid, "issues": issues}


@router.post("/merge")
def merge_session_cart(
    merge_request: CartMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Merge anonymous session cart into user's cart.
    Called after login to transfer items from session cart.
    """
    merged_cart = CartService.merge_session_cart(db, current_user, merge_request.session_id)
    
    if merged_cart:
        return {"message": "Cart merged successfully", "item_count": merged_cart.item_count}
    
    return {"message": "No session cart to merge"}


# =============================================================================
# SESSION CART ENDPOINTS (Anonymous Users)
# =============================================================================

@router.get("/session/{session_id}", response_model=CartResponse)
def get_session_cart(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get anonymous session cart"""
    cart = CartService.get_or_create_cart(db, session_id=session_id)
    
    is_valid, issues = CartService.validate_cart_for_checkout(db, cart)
    
    return _build_cart_response(cart, not is_valid, issues)


@router.post("/session/{session_id}/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_session_cart(
    session_id: str,
    item: CartItemCreate,
    db: Session = Depends(get_db)
):
    """Add item to anonymous session cart"""
    cart = CartService.get_or_create_cart(db, session_id=session_id)
    
    try:
        cart_item = CartService.add_item(db, cart, item)
        return _build_cart_item_response(cart_item)
    except CartError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/session/{session_id}/items/{item_id}", response_model=CartItemResponse)
def update_session_cart_item(
    session_id: str,
    item_id: int,
    item_update: CartItemUpdate,
    db: Session = Depends(get_db)
):
    """Update item quantity in session cart"""
    cart = CartService.get_cart(db, session_id=session_id)
    
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    
    try:
        cart_item = CartService.update_item_quantity(db, cart, item_id, item_update.quantity)
        return _build_cart_item_response(cart_item)
    except CartError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/session/{session_id}/items/{item_id}")
def remove_from_session_cart(
    session_id: str,
    item_id: int,
    db: Session = Depends(get_db)
):
    """Remove item from session cart"""
    cart = CartService.get_cart(db, session_id=session_id)
    
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    
    try:
        CartService.remove_item(db, cart, item_id)
        return {"message": "Item removed from cart"}
    except CartError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/session/{session_id}")
def clear_session_cart(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Clear session cart"""
    cart = CartService.get_cart(db, session_id=session_id)
    
    if cart:
        CartService.clear_cart(db, cart)
    
    return {"message": "Cart cleared successfully"}


@router.get("/session/new")
def generate_session_id():
    """Generate a new session ID for anonymous cart"""
    return {"session_id": CartService.generate_session_id()}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _build_cart_response(cart: Cart, has_issues: bool, issues: list) -> CartResponse:
    """Build CartResponse from Cart model"""
    return CartResponse(
        id=cart.id,
        user_id=cart.user_id,
        session_id=cart.session_id,
        status=cart.status,
        promo_code=cart.promo_code,
        items=[_build_cart_item_response(item) for item in cart.items],
        subtotal=cart.subtotal or 0,
        tax_amount=cart.tax_amount or 0,
        discount_amount=cart.discount_amount or 0,
        total=cart.total or 0,
        item_count=cart.item_count,
        created_at=cart.created_at,
        updated_at=cart.updated_at,
        expires_at=cart.expires_at,
        has_stock_issues=has_issues,
        stock_warnings=issues,
    )


def _build_cart_item_response(item: CartItemModel) -> CartItemResponse:
    """Build CartItemResponse from CartItem model"""
    from app.schemas.cart import CartItemProductInfo, CartItemVariationInfo
    
    product_info = None
    variation_info = None
    available_quantity = 0
    in_stock = True
    
    if item.product:
        product_info = CartItemProductInfo(
            id=item.product.id,
            name=item.product.name,
            slug=item.product.slug,
            price=item.product.price,
            original_price=item.product.original_price,
            primary_image=item.product.primary_image,
            thumbnail=item.product.thumbnail,
            stock=item.product.stock,
            is_active=item.product.is_active,
        )
        available_quantity = item.product.stock
        in_stock = item.product.stock >= item.quantity
    
    if item.variation:
        variation_info = CartItemVariationInfo(
            id=item.variation.id,
            name=item.variation.name,
            value=getattr(item.variation, 'value', None),
            price_modifier=getattr(item.variation, 'price_modifier', None),
            stock=item.variation.stock,
        )
        if item.variation.stock is not None:
            available_quantity = item.variation.stock
            in_stock = item.variation.stock >= item.quantity
    
    # Calculate line total
    price = float(item.unit_price) if item.unit_price else (
        float(item.product.price) if item.product else 0
    )
    line_total = price * item.quantity
    
    return CartItemResponse(
        id=item.id,
        cart_id=item.cart_id,
        product_id=item.product_id,
        variation_id=item.variation_id,
        quantity=item.quantity,
        unit_price=item.unit_price,
        line_total=line_total,
        is_reserved=item.is_reserved,
        reserved_until=item.reserved_until,
        created_at=item.created_at,
        updated_at=item.updated_at,
        product=product_info,
        variation=variation_info,
        in_stock=in_stock,
        available_quantity=available_quantity,
    )
