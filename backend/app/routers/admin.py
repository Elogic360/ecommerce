from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models.customer import User, Role
from app.models.order import Order
from app.schemas.user import UserOut, UserUpdate
from app.core.security import get_current_admin_user
from sqlalchemy import func, desc
from decimal import Decimal

router = APIRouter()

# ==================== ADMIN USER MANAGEMENT ====================

@router.get("/users", response_model=List[UserOut])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all users (Admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get user by ID (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update user (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete user (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get dashboard statistics (Admin only)"""
    from app.models.product import Product
    from app.models.order import Order
    from sqlalchemy import func
    
    total_users = db.query(func.count(User.id)).scalar()
    total_products = db.query(func.count(Product.id)).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.payment_status == "paid"
    ).scalar() or 0
    
    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": float(total_revenue)
    }


# ==================== ADMIN ORDERS MANAGEMENT ====================

@router.get("/orders")
def get_admin_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all orders with filtering (Admin only)"""
    query = db.query(Order)
    
    # Apply filters
    if status:
        query = query.filter(Order.status == status)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Order.order_number.ilike(search_term)) |
            (Order.guest_email.ilike(search_term)) |
            (Order.guest_name.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    
    # Get orders
    orders = query.order_by(desc(Order.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return {
        "items": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer_name": order.guest_name or (order.user.full_name if order.user else "Guest"),
                "customer_email": order.guest_email or (order.user.email if order.user else None),
                "total_amount": float(order.total_amount),
                "status": order.status,
                "payment_status": order.payment_status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "items_count": len(order.items) if order.items else 0
            }
            for order in orders
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/orders/{order_id}")
def get_admin_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get order details (Admin only)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get address info if available
    shipping_address = None
    if order.address:
        shipping_address = {
            "street": order.address.street if hasattr(order.address, 'street') else None,
            "city": order.address.city if hasattr(order.address, 'city') else None,
            "state": order.address.state if hasattr(order.address, 'state') else None,
            "postal_code": order.address.postal_code if hasattr(order.address, 'postal_code') else None,
            "country": order.address.country if hasattr(order.address, 'country') else None
        }
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "user_id": order.user_id,
        "customer_name": order.guest_name or (order.user.full_name if order.user else "Guest"),
        "customer_email": order.guest_email or (order.user.email if order.user else None),
        "customer_phone": order.guest_phone or None,
        "shipping_address": shipping_address,
        "billing_address": None,  # Add if exists in model
        "subtotal": float(order.subtotal),
        "shipping_cost": float(order.shipping_cost) if order.shipping_cost else 0,
        "tax_amount": float(order.tax_amount) if order.tax_amount else 0,
        "discount_amount": float(order.discount_amount) if order.discount_amount else 0,
        "total_amount": float(order.total_amount),
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "tracking_number": order.tracking_number,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.unit_price * item.quantity)
            }
            for item in (order.items or [])
        ]
    }


@router.put("/orders/{order_id}/status")
def update_admin_order_status(
    order_id: int,
    status: str = Query(...),
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update order status (Admin only)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = status
    if notes:
        order.notes = notes
    
    db.commit()
    db.refresh(order)
    
    return {"message": "Order status updated", "status": order.status}


@router.post("/orders/{order_id}/cancel")
def cancel_admin_order(
    order_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Cancel an order (Admin only)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Order is already cancelled")
    
    if order.status in ["delivered", "completed"]:
        raise HTTPException(status_code=400, detail="Cannot cancel delivered/completed orders")
    
    order.status = "cancelled"
    if reason:
        order.notes = f"Cancelled: {reason}"
    
    db.commit()
    
    return {"message": "Order cancelled successfully"}
