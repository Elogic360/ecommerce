"""
Cart Service - Business logic for shopping cart operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.models.cart import Cart, CartItem, CartStatus
from app.models.product import Product, ProductVariation
from app.models.customer import User
from app.schemas.cart import (
    CartItemCreate, CartItemUpdate, CartResponse, 
    CartItemResponse, CartSummary
)


class CartError(Exception):
    """Custom exception for cart-related errors"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class CartService:
    """Service class for cart operations"""
    
    # Configuration
    MAX_QUANTITY_PER_ITEM = 10
    CART_EXPIRATION_HOURS = 72
    TAX_RATE = Decimal("0.18")  # 18% VAT
    FREE_SHIPPING_THRESHOLD = Decimal("50000")  # Free shipping over 50,000
    SHIPPING_COST = Decimal("5000")  # Default shipping cost
    
    @classmethod
    def get_or_create_cart(
        cls,
        db: Session,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Cart:
        """
        Get existing cart or create new one.
        Supports both authenticated users and anonymous sessions.
        """
        cart = None
        
        if user_id:
            # Look for user's active cart
            cart = db.query(Cart).filter(
                and_(
                    Cart.user_id == user_id,
                    Cart.status == CartStatus.ACTIVE.value
                )
            ).first()
        elif session_id:
            # Look for session cart
            cart = db.query(Cart).filter(
                and_(
                    Cart.session_id == session_id,
                    Cart.status == CartStatus.ACTIVE.value
                )
            ).first()
        
        if not cart:
            # Create new cart
            cart = Cart(
                user_id=user_id,
                session_id=session_id if not user_id else None,
                status=CartStatus.ACTIVE.value,
            )
            cart.set_expiration(cls.CART_EXPIRATION_HOURS)
            db.add(cart)
            db.commit()
            db.refresh(cart)
        else:
            # Check if cart has expired
            if cart.is_expired:
                cart.status = CartStatus.EXPIRED.value
                db.commit()
                # Create new cart
                cart = Cart(
                    user_id=user_id,
                    session_id=session_id if not user_id else None,
                    status=CartStatus.ACTIVE.value,
                )
                cart.set_expiration(cls.CART_EXPIRATION_HOURS)
                db.add(cart)
                db.commit()
                db.refresh(cart)
            else:
                # Refresh expiration on activity
                cart.refresh_expiration(cls.CART_EXPIRATION_HOURS)
                db.commit()
        
        return cart
    
    @classmethod
    def get_cart(
        cls,
        db: Session,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Optional[Cart]:
        """Get cart without creating if doesn't exist"""
        if user_id:
            return db.query(Cart).filter(
                and_(
                    Cart.user_id == user_id,
                    Cart.status == CartStatus.ACTIVE.value
                )
            ).first()
        elif session_id:
            return db.query(Cart).filter(
                and_(
                    Cart.session_id == session_id,
                    Cart.status == CartStatus.ACTIVE.value
                )
            ).first()
        return None
    
    @classmethod
    def add_item(
        cls,
        db: Session,
        cart: Cart,
        item_data: CartItemCreate
    ) -> CartItem:
        """
        Add item to cart with validation.
        - Validates product exists and is active
        - Validates stock availability
        - Enforces max quantity per item
        - Updates or creates cart item
        """
        # Validate product
        product = db.query(Product).filter(
            and_(
                Product.id == item_data.product_id,
                Product.is_active == True
            )
        ).first()
        
        if not product:
            raise CartError("Product not found or not available", status.HTTP_404_NOT_FOUND)
        
        # Validate variation if provided
        variation = None
        available_stock = product.stock
        
        if item_data.variation_id:
            variation = db.query(ProductVariation).filter(
                and_(
                    ProductVariation.id == item_data.variation_id,
                    ProductVariation.product_id == item_data.product_id
                )
            ).first()
            
            if not variation:
                raise CartError("Product variation not found", status.HTTP_404_NOT_FOUND)
            
            if variation.stock is not None:
                available_stock = variation.stock
        
        # Check existing item in cart
        existing_item = db.query(CartItem).filter(
            and_(
                CartItem.cart_id == cart.id,
                CartItem.product_id == item_data.product_id,
                CartItem.variation_id == item_data.variation_id
            )
        ).first()
        
        new_quantity = item_data.quantity
        if existing_item:
            new_quantity = existing_item.quantity + item_data.quantity
        
        # Validate quantity limits
        if new_quantity > cls.MAX_QUANTITY_PER_ITEM:
            raise CartError(
                f"Maximum quantity per item is {cls.MAX_QUANTITY_PER_ITEM}",
                status.HTTP_400_BAD_REQUEST
            )
        
        # Validate stock
        if new_quantity > available_stock:
            raise CartError(
                f"Insufficient stock. Only {available_stock} items available",
                status.HTTP_400_BAD_REQUEST
            )
        
        if existing_item:
            # Update quantity
            existing_item.quantity = new_quantity
            existing_item.unit_price = product.price
            db.commit()
            db.refresh(existing_item)
            cls._update_cart_totals(db, cart)
            return existing_item
        else:
            # Create new cart item
            cart_item = CartItem(
                cart_id=cart.id,
                user_id=cart.user_id,
                product_id=item_data.product_id,
                variation_id=item_data.variation_id,
                quantity=item_data.quantity,
                unit_price=product.price,
            )
            db.add(cart_item)
            db.commit()
            db.refresh(cart_item)
            cls._update_cart_totals(db, cart)
            return cart_item
    
    @classmethod
    def update_item_quantity(
        cls,
        db: Session,
        cart: Cart,
        item_id: int,
        quantity: int
    ) -> CartItem:
        """Update cart item quantity with validation"""
        cart_item = db.query(CartItem).filter(
            and_(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id
            )
        ).first()
        
        if not cart_item:
            raise CartError("Cart item not found", status.HTTP_404_NOT_FOUND)
        
        # Validate quantity limit
        if quantity > cls.MAX_QUANTITY_PER_ITEM:
            raise CartError(
                f"Maximum quantity per item is {cls.MAX_QUANTITY_PER_ITEM}",
                status.HTTP_400_BAD_REQUEST
            )
        
        # Validate stock
        product = cart_item.product
        available_stock = product.stock
        
        if cart_item.variation_id and cart_item.variation:
            if cart_item.variation.stock is not None:
                available_stock = cart_item.variation.stock
        
        if quantity > available_stock:
            raise CartError(
                f"Insufficient stock. Only {available_stock} items available",
                status.HTTP_400_BAD_REQUEST
            )
        
        cart_item.quantity = quantity
        cart_item.unit_price = product.price  # Update price
        db.commit()
        db.refresh(cart_item)
        cls._update_cart_totals(db, cart)
        return cart_item
    
    @classmethod
    def remove_item(cls, db: Session, cart: Cart, item_id: int) -> bool:
        """Remove item from cart"""
        cart_item = db.query(CartItem).filter(
            and_(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id
            )
        ).first()
        
        if not cart_item:
            raise CartError("Cart item not found", status.HTTP_404_NOT_FOUND)
        
        db.delete(cart_item)
        db.commit()
        cls._update_cart_totals(db, cart)
        return True
    
    @classmethod
    def clear_cart(cls, db: Session, cart: Cart) -> bool:
        """Remove all items from cart"""
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        cart.subtotal = Decimal("0")
        cart.tax_amount = Decimal("0")
        cart.total = Decimal("0")
        cart.discount_amount = Decimal("0")
        db.commit()
        return True
    
    @classmethod
    def _update_cart_totals(cls, db: Session, cart: Cart) -> None:
        """Recalculate and update cart totals"""
        subtotal = Decimal("0")
        
        for item in cart.items:
            price = item.unit_price or item.product.price
            subtotal += Decimal(str(price)) * item.quantity
        
        tax_amount = subtotal * cls.TAX_RATE
        
        # Apply shipping
        shipping = Decimal("0")
        if subtotal < cls.FREE_SHIPPING_THRESHOLD and subtotal > 0:
            shipping = cls.SHIPPING_COST
        
        # Apply discount
        discount = cart.discount_amount or Decimal("0")
        
        total = subtotal + tax_amount + shipping - discount
        
        cart.subtotal = subtotal
        cart.tax_amount = tax_amount
        cart.total = total
        db.commit()
    
    @classmethod
    def get_cart_summary(cls, db: Session, cart: Cart) -> CartSummary:
        """Get cart summary with totals"""
        cls._update_cart_totals(db, cart)
        
        shipping_estimate = Decimal("0")
        if cart.subtotal and cart.subtotal < cls.FREE_SHIPPING_THRESHOLD and cart.subtotal > 0:
            shipping_estimate = cls.SHIPPING_COST
        
        return CartSummary(
            item_count=cart.item_count,
            subtotal=cart.subtotal or Decimal("0"),
            tax_amount=cart.tax_amount or Decimal("0"),
            shipping_estimate=shipping_estimate,
            discount_amount=cart.discount_amount or Decimal("0"),
            total=cart.total or Decimal("0"),
        )
    
    @classmethod
    def validate_cart_for_checkout(cls, db: Session, cart: Cart) -> Tuple[bool, List[str]]:
        """
        Validate cart is ready for checkout.
        Returns (is_valid, list of issues)
        """
        issues = []
        
        if not cart.items:
            issues.append("Cart is empty")
            return False, issues
        
        for item in cart.items:
            product = item.product
            
            # Check product is still active
            if not product or not product.is_active:
                issues.append(f"Product '{product.name if product else 'Unknown'}' is no longer available")
                continue
            
            # Check stock
            available_stock = product.stock
            if item.variation_id and item.variation:
                if item.variation.stock is not None:
                    available_stock = item.variation.stock
            
            if item.quantity > available_stock:
                issues.append(
                    f"'{product.name}' has only {available_stock} items in stock (you have {item.quantity})"
                )
        
        return len(issues) == 0, issues
    
    @classmethod
    def merge_session_cart(
        cls,
        db: Session,
        user: User,
        session_id: str
    ) -> Optional[Cart]:
        """
        Merge anonymous session cart into user's cart.
        Called when user logs in.
        """
        session_cart = db.query(Cart).filter(
            and_(
                Cart.session_id == session_id,
                Cart.status == CartStatus.ACTIVE.value
            )
        ).first()
        
        if not session_cart or not session_cart.items:
            return None
        
        # Get or create user cart
        user_cart = cls.get_or_create_cart(db, user_id=user.id)
        
        # Merge items
        for session_item in session_cart.items:
            try:
                cls.add_item(
                    db, 
                    user_cart,
                    CartItemCreate(
                        product_id=session_item.product_id,
                        variation_id=session_item.variation_id,
                        quantity=session_item.quantity
                    )
                )
            except CartError:
                # Skip items that can't be added (out of stock, etc.)
                pass
        
        # Mark session cart as converted
        session_cart.status = CartStatus.CONVERTED.value
        db.commit()
        
        return user_cart
    
    @classmethod
    def apply_promo_code(
        cls,
        db: Session,
        cart: Cart,
        promo_code: str
    ) -> Tuple[bool, str]:
        """
        Apply promo code to cart.
        Returns (success, message)
        
        TODO: Implement promo code validation against promotions table
        """
        # Placeholder for promo code validation
        # In production, query promotions table
        
        cart.promo_code = promo_code
        # cart.discount_amount = calculated_discount
        db.commit()
        cls._update_cart_totals(db, cart)
        
        return True, "Promo code applied"
    
    @classmethod
    def mark_cart_converted(cls, db: Session, cart: Cart) -> None:
        """Mark cart as converted after order creation"""
        cart.status = CartStatus.CONVERTED.value
        db.commit()
    
    @classmethod
    def cleanup_expired_carts(cls, db: Session) -> int:
        """
        Cleanup expired carts (batch job).
        Returns number of carts cleaned up.
        """
        expired_carts = db.query(Cart).filter(
            and_(
                Cart.expires_at < datetime.utcnow(),
                Cart.status == CartStatus.ACTIVE.value
            )
        ).all()
        
        count = 0
        for cart in expired_carts:
            cart.status = CartStatus.EXPIRED.value
            count += 1
        
        db.commit()
        return count
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate a unique session ID for anonymous carts"""
        return str(uuid.uuid4())
