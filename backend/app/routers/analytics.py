"""
Analytics Router
Admin analytics and reporting endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional, Any
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.session import get_db
from app.models.customer import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.features import ProductView
from app.schemas.features import AnalyticsSummary, ProductViewStats, ProductViewCreate
from app.core.security import get_current_user, get_current_admin_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


# Helper to get optional current user
async def get_current_user_optional(db: Session = Depends(get_db)) -> Optional[Any]:
    """Get current user if authenticated, None otherwise"""
    return None  # Anonymous tracking allowed


# =============================================================================
# PUBLIC ENDPOINTS (tracking)
# =============================================================================

@router.post("/track-view", status_code=201, response_model=None)
def track_product_view(
    data: ProductViewCreate,
    db: Session = Depends(get_db),
):
    """Track a product page view (can be anonymous)"""
    view = ProductView(
        user_id=None,  # For now, anonymous tracking
        product_id=data.product_id,
        session_id=data.session_id,
        duration_seconds=data.duration_seconds,
        device_type=data.device_type,
        referrer=data.referrer,
    )
    db.add(view)

    # Increment product view count
    db.query(Product).filter(Product.id == data.product_id).update(
        {"view_count": Product.view_count + 1}
    )

    db.commit()
    return {"status": "tracked"}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/dashboard", response_model=AnalyticsSummary)
def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get main dashboard analytics summary"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    # Total orders
    total_orders = db.query(func.count(Order.id)).scalar()

    # Total revenue
    total_revenue = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.payment_status == "paid")
        .scalar()
    )

    # Total customers
    total_customers = db.query(func.count(User.id)).filter(User.role == "user").scalar()

    # Total products
    total_products = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar()

    # Today's orders
    orders_today = (
        db.query(func.count(Order.id))
        .filter(Order.created_at >= today_start)
        .scalar()
    )

    # Today's revenue
    revenue_today = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.created_at >= today_start, Order.payment_status == "paid")
        .scalar()
    )

    # Top products by sales
    top_products = (
        db.query(
            Product.id,
            Product.name,
            func.sum(OrderItem.quantity).label("total_sold"),
            func.sum(OrderItem.quantity * OrderItem.price).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id)
        .order_by(desc("total_sold"))
        .limit(5)
        .all()
    )

    # Recent orders
    recent_orders = (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )

    return AnalyticsSummary(
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_customers=total_customers,
        total_products=total_products,
        orders_today=orders_today,
        revenue_today=revenue_today,
        top_products=[
            {
                "id": p.id,
                "name": p.name,
                "total_sold": p.total_sold,
                "revenue": float(p.revenue),
            }
            for p in top_products
        ],
        recent_orders=[
            {
                "id": o.id,
                "order_number": o.order_number,
                "total_amount": float(o.total_amount),
                "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in recent_orders
        ],
    )


@router.get("/revenue")
def get_revenue_analytics(
    period: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get revenue analytics over time"""
    days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = days_map[period]
    start_date = datetime.utcnow() - timedelta(days=days)

    # Daily revenue
    daily_revenue = (
        db.query(
            func.date(Order.created_at).label("date"),
            func.sum(Order.total_amount).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .filter(Order.created_at >= start_date, Order.payment_status == "paid")
        .group_by(func.date(Order.created_at))
        .order_by("date")
        .all()
    )

    return {
        "period": period,
        "data": [
            {
                "date": str(row.date),
                "revenue": float(row.revenue),
                "orders": row.orders,
            }
            for row in daily_revenue
        ],
    }


@router.get("/products/performance")
def get_product_performance(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get product performance metrics"""
    products = (
        db.query(
            Product.id,
            Product.name,
            Product.price,
            Product.stock,
            Product.view_count,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0).label("revenue"),
        )
        .outerjoin(OrderItem, OrderItem.product_id == Product.id)
        .filter(Product.is_active == True)
        .group_by(Product.id)
        .order_by(desc("revenue"))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "stock": p.stock,
            "view_count": p.view_count,
            "units_sold": p.units_sold,
            "revenue": float(p.revenue),
            "conversion_rate": round((p.units_sold / max(p.view_count, 1)) * 100, 2),
        }
        for p in products
    ]


@router.get("/customers/insights")
def get_customer_insights(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get customer insights and segmentation"""
    # Total customers by loyalty tier
    tier_distribution = (
        db.query(User.loyalty_tier, func.count(User.id))
        .filter(User.role == "user")
        .group_by(User.loyalty_tier)
        .all()
    )

    # New customers this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_customers_month = (
        db.query(func.count(User.id))
        .filter(User.role == "user", User.created_at >= month_start)
        .scalar()
    )

    # Top customers by order value
    top_customers = (
        db.query(
            User.id,
            User.email,
            User.full_name,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_spent"),
        )
        .join(Order, Order.user_id == User.id)
        .filter(Order.payment_status == "paid")
        .group_by(User.id)
        .order_by(desc("total_spent"))
        .limit(10)
        .all()
    )

    return {
        "tier_distribution": {tier: count for tier, count in tier_distribution},
        "new_customers_this_month": new_customers_month,
        "top_customers": [
            {
                "id": c.id,
                "email": c.email,
                "name": c.full_name,
                "order_count": c.order_count,
                "total_spent": float(c.total_spent),
            }
            for c in top_customers
        ],
    }


@router.get("/products/{product_id}/views", response_model=ProductViewStats)
def get_product_view_stats(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get view statistics for a specific product"""
    total_views = (
        db.query(func.count(ProductView.id))
        .filter(ProductView.product_id == product_id)
        .scalar()
    )

    unique_users = (
        db.query(func.count(func.distinct(ProductView.user_id)))
        .filter(ProductView.product_id == product_id, ProductView.user_id.isnot(None))
        .scalar()
    )

    avg_duration = (
        db.query(func.avg(ProductView.duration_seconds))
        .filter(ProductView.product_id == product_id, ProductView.duration_seconds.isnot(None))
        .scalar()
    )

    return ProductViewStats(
        product_id=product_id,
        total_views=total_views,
        unique_users=unique_users,
        avg_duration=float(avg_duration) if avg_duration else None,
    )
