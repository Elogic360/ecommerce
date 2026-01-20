from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.cart import CartItem
from app.models.product import Product
from app.models.customer import User, Address
from app.schemas.order import OrderCreate, OrderUpdate, Order as OrderSchema
from app.core.security import get_current_user, get_current_admin_user
import random
import string
from datetime import datetime

router = APIRouter()

def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{timestamp}-{random_str}"

@router.post("/orders", response_model=OrderSchema)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify address belongs to user
    address = db.query(Address).filter(
        Address.id == order.address_id,
        Address.user_id == current_user.id
    ).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # Calculate totals
    total_amount = 0
    order_items = []
    
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        # Check stock
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock for {product.name}"
            )
        
        # Calculate item total
        item_price = product.price
        item_total = item_price * item.quantity
        total_amount += item_total
        
        order_items.append({
            "product_id": item.product_id,
            "variation_id": item.variation_id,
            "quantity": item.quantity,
            "price": item_price
        })
        
        # Update stock
        product.stock -= item.quantity
    
    # Add shipping and tax
    shipping_cost = 5000.0 if total_amount < 50000 else 0.0  # Free shipping over TZS 50,000
    tax_amount = total_amount * 0.18  # 18% VAT
    final_total = total_amount + shipping_cost + tax_amount
    
    # Create order
    db_order = Order(
        user_id=current_user.id,
        address_id=order.address_id,
        order_number=generate_order_number(),
        total_amount=final_total,
        shipping_cost=shipping_cost,
        tax_amount=tax_amount,
        payment_method=order.payment_method,
        notes=order.notes,
        status="pending",
        payment_status="pending"
    )
    
    db.add(db_order)
    db.flush()
    
    # Create order items
    for item_data in order_items:
        order_item = OrderItem(
            order_id=db_order.id,
            **item_data
        )
        db.add(order_item)
    
    # Clear cart
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    
    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/orders", response_model=List[OrderSchema])
def get_user_orders(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    orders = db.query(Order).filter(Order.user_id == current_user.id)\
        .order_by(Order.created_at.desc())\
        .offset(skip).limit(limit).all()
    return orders

@router.get("/orders/{order_id}", response_model=OrderSchema)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

# Admin endpoints
@router.get("/admin/orders", response_model=List[OrderSchema])
def get_all_orders(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc())\
        .offset(skip).limit(limit).all()
    return orders

@router.put("/admin/orders/{order_id}", response_model=OrderSchema)
def update_order_status(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order

@router.delete("/admin/orders/{order_id}")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status in ["shipped", "delivered"]:
        raise HTTPException(
            status_code=400, 
            detail="Cannot cancel order that has been shipped or delivered"
        )
    
    # Restore stock
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity
    
    order.status = "cancelled"
    db.commit()
    
    return {"message": "Order cancelled successfully"}
