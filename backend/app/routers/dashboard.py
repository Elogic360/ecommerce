"""
Admin Dashboard Router
Provides dashboard statistics, charts data, and quick overviews for admin panel
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal

from app.db.session import get_db
from app.models.customer import User
from app.models.product import Product, Category
from app.models.order import Order, OrderItem
from app.core.security import get_current_admin_user

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get main dashboard statistics"""
    # Total counts
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_products = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    
    # Revenue calculation
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.payment_status == "paid"
    ).scalar() or Decimal("0")
    
    # Today's stats
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    today_orders = db.query(func.count(Order.id)).filter(
        Order.created_at >= today_start
    ).scalar() or 0
    
    today_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= today_start,
        Order.payment_status == "paid"
    ).scalar() or Decimal("0")
    
    # This month's stats
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    
    monthly_orders = db.query(func.count(Order.id)).filter(
        Order.created_at >= month_start_dt
    ).scalar() or 0
    
    monthly_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= month_start_dt,
        Order.payment_status == "paid"
    ).scalar() or Decimal("0")
    
    # Pending orders
    pending_orders = db.query(func.count(Order.id)).filter(
        Order.status.in_(["pending", "processing"])
    ).scalar() or 0
    
    # Low stock products count
    low_stock_count = db.query(func.count(Product.id)).filter(
        Product.stock < 10,
        Product.is_active == True
    ).scalar() or 0
    
    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
        "today_orders": today_orders,
        "today_revenue": float(today_revenue),
        "monthly_orders": monthly_orders,
        "monthly_revenue": float(monthly_revenue),
        "pending_orders": pending_orders,
        "low_stock_count": low_stock_count
    }


@router.get("/sales")
def get_sales_data(
    period: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get sales data for charts"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get orders with their dates and amounts
    orders = db.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(
        Order.created_at >= start_date,
        Order.payment_status == "paid"
    ).group_by(
        func.date(Order.created_at)
    ).order_by(
        func.date(Order.created_at)
    ).all()
    
    # Format for chart
    sales_data = []
    for order in orders:
        sales_data.append({
            "date": order.date.isoformat() if order.date else None,
            "orders": order.order_count or 0,
            "revenue": float(order.revenue or 0)
        })
    
    return {
        "period": period,
        "days": days,
        "data": sales_data
    }


@router.get("/top-products")
def get_top_products(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get top selling products"""
    try:
        # Get products with order counts
        top_products = db.query(
            Product.id,
            Product.name,
            Product.price,
            Product.stock,
            Product.primary_image,
            func.coalesce(func.sum(OrderItem.quantity), 0).label('total_sold'),
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0).label('total_revenue')
        ).outerjoin(
            OrderItem, OrderItem.product_id == Product.id
        ).outerjoin(
            Order, Order.id == OrderItem.order_id
        ).filter(
            Product.is_active == True
        ).group_by(
            Product.id
        ).order_by(
            desc('total_sold')
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price) if p.price else 0,
                "stock": p.stock or 0,
                "image": p.primary_image,
                "total_sold": int(p.total_sold or 0),
                "revenue": float(p.total_revenue or 0)
            }
            for p in top_products
        ]
    except Exception as e:
        # Fallback: return products without sales data
        products = db.query(Product).filter(
            Product.is_active == True
        ).limit(limit).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price) if p.price else 0,
                "stock": p.stock or 0,
                "image": p.primary_image,
                "total_sold": 0,
                "revenue": 0
            }
            for p in products
        ]


@router.get("/category-sales")
def get_category_sales(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get sales by category"""
    try:
        from app.models.product import ProductCategoryAssociation
        
        # Get all categories with their sales data
        categories = db.query(Category).all()
        result = []
        
        for cat in categories:
            # Count orders and revenue for this category
            sales_data = db.query(
                func.count(OrderItem.id).label('order_count'),
                func.coalesce(func.sum(OrderItem.quantity), 0).label('items_sold'),
                func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0).label('revenue')
            ).join(
                Product, Product.id == OrderItem.product_id
            ).join(
                ProductCategoryAssociation,
                ProductCategoryAssociation.product_id == Product.id
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                ProductCategoryAssociation.category_id == cat.id,
                Order.payment_status == "paid"
            ).first()
            
            result.append({
                "id": cat.id,
                "name": cat.name,
                "order_count": sales_data.order_count if sales_data else 0,
                "items_sold": int(sales_data.items_sold) if sales_data and sales_data.items_sold else 0,
                "revenue": float(sales_data.revenue) if sales_data and sales_data.revenue else 0
            })
        
        # Sort by revenue descending
        result.sort(key=lambda x: x['revenue'], reverse=True)
        return result
    except Exception as e:
        # Fallback: return categories without sales data
        categories = db.query(Category).all()
        return [
            {
                "id": cat.id,
                "name": cat.name,
                "order_count": 0,
                "items_sold": 0,
                "revenue": 0
            }
            for cat in categories
        ]


@router.get("/recent-orders")
def get_recent_orders(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get recent orders for dashboard"""
    orders = db.query(Order).order_by(
        desc(Order.created_at)
    ).limit(limit).all()
    
    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": order.guest_name or (order.user.full_name if order.user else "Guest"),
            "customer_email": order.guest_email or (order.user.email if order.user else None),
            "total_amount": float(order.total_amount),
            "status": order.status,
            "payment_status": order.payment_status,
            "created_at": order.created_at.isoformat() if order.created_at else None
        }
        for order in orders
    ]


@router.get("/low-stock")
def get_low_stock_products(
    limit: int = Query(5, ge=1, le=50),
    threshold: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get products with low stock"""
    products = db.query(Product).filter(
        Product.stock < threshold,
        Product.is_active == True
    ).order_by(
        Product.stock
    ).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "stock": p.stock,
            "price": float(p.price),
            "image": p.primary_image
        }
        for p in products
    ]
