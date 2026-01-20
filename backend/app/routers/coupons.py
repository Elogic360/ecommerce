"""
Coupon Router
CRUD and validation endpoints for discount coupons.
"""
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import get_db
from app.models.customer import User
from app.models.features import Coupon, CouponUsage
from app.schemas.features import (
    Coupon as CouponSchema,
    CouponCreate,
    CouponUpdate,
    CouponValidation,
    CouponValidationResult,
)
from app.core.security import get_current_user, get_current_admin_user

router = APIRouter(prefix="/coupons", tags=["coupons"])


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@router.post("/validate", response_model=CouponValidationResult)
def validate_coupon(
    data: CouponValidation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate a coupon code for the current cart"""
    coupon = db.query(Coupon).filter(
        Coupon.code == data.code.upper(),
        Coupon.is_active == True,
    ).first()

    if not coupon:
        return CouponValidationResult(valid=False, message="Invalid coupon code")

    now = datetime.utcnow()

    # Check validity period
    if coupon.valid_from and coupon.valid_from > now:
        return CouponValidationResult(valid=False, message="Coupon is not yet active")
    if coupon.valid_until and coupon.valid_until < now:
        return CouponValidationResult(valid=False, message="Coupon has expired")

    # Check usage limit
    if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
        return CouponValidationResult(valid=False, message="Coupon usage limit reached")

    # Check if user already used this coupon
    user_usage = db.query(CouponUsage).filter(
        CouponUsage.coupon_id == coupon.id,
        CouponUsage.user_id == current_user.id,
    ).first()
    if user_usage:
        return CouponValidationResult(valid=False, message="You have already used this coupon")

    # Check minimum purchase
    if coupon.min_purchase_amount and data.cart_total < coupon.min_purchase_amount:
        return CouponValidationResult(
            valid=False,
            message=f"Minimum purchase of ${coupon.min_purchase_amount} required"
        )

    # Check applicable categories/products
    if coupon.applicable_categories and data.category_ids:
        if not any(cat_id in coupon.applicable_categories for cat_id in data.category_ids):
            return CouponValidationResult(valid=False, message="Coupon not valid for these categories")

    if coupon.applicable_products and data.product_ids:
        if not any(prod_id in coupon.applicable_products for prod_id in data.product_ids):
            return CouponValidationResult(valid=False, message="Coupon not valid for these products")

    # Calculate discount
    discount_amount = Decimal("0")
    if coupon.discount_type == "percentage":
        discount_amount = data.cart_total * (coupon.discount_value / 100)
        if coupon.max_discount_amount:
            discount_amount = min(discount_amount, coupon.max_discount_amount)
    elif coupon.discount_type == "fixed":
        discount_amount = min(coupon.discount_value, data.cart_total)
    elif coupon.discount_type == "free_shipping":
        discount_amount = Decimal("0")  # Shipping handled separately

    return CouponValidationResult(
        valid=True,
        discount_amount=discount_amount,
        message="Coupon applied successfully",
        coupon=coupon,
    )


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("", response_model=List[CouponSchema])
def list_coupons(
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """List all coupons (admin only)"""
    query = db.query(Coupon)
    if is_active is not None:
        query = query.filter(Coupon.is_active == is_active)
    return query.order_by(Coupon.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=CouponSchema, status_code=status.HTTP_201_CREATED)
def create_coupon(
    data: CouponCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Create a new coupon (admin only)"""
    # Check code uniqueness
    existing = db.query(Coupon).filter(Coupon.code == data.code.upper()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon code already exists")

    coupon_data = data.model_dump()
    coupon_data['code'] = coupon_data['code'].upper()
    coupon = Coupon(**coupon_data)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.get("/{coupon_id}", response_model=CouponSchema)
def get_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get coupon details (admin only)"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    return coupon


@router.patch("/{coupon_id}", response_model=CouponSchema)
def update_coupon(
    coupon_id: int,
    data: CouponUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Update a coupon (admin only)"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(coupon, field, value)

    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Delete a coupon (admin only)"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")

    db.delete(coupon)
    db.commit()
