"""
Loyalty Router
Endpoints for loyalty points management and redemption.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.customer import User
from app.models.features import LoyaltyPoint
from app.schemas.features import (
    LoyaltyPoint as LoyaltyPointSchema,
    LoyaltyPointCreate,
    LoyaltyBalance,
    LoyaltyRedemption,
)
from app.core.security import get_current_user, get_current_admin_user

router = APIRouter(prefix="/loyalty", tags=["loyalty"])

# Tier thresholds
TIER_THRESHOLDS = {
    "bronze": 0,
    "silver": 500,
    "gold": 2000,
    "platinum": 5000,
}


def get_tier(points: int) -> str:
    """Determine loyalty tier based on points"""
    if points >= TIER_THRESHOLDS["platinum"]:
        return "platinum"
    elif points >= TIER_THRESHOLDS["gold"]:
        return "gold"
    elif points >= TIER_THRESHOLDS["silver"]:
        return "silver"
    return "bronze"


def get_points_to_next_tier(current_points: int, current_tier: str) -> int:
    """Calculate points needed for next tier"""
    tiers = list(TIER_THRESHOLDS.keys())
    current_idx = tiers.index(current_tier)
    if current_idx >= len(tiers) - 1:
        return 0  # Already at highest tier
    next_tier = tiers[current_idx + 1]
    return max(0, TIER_THRESHOLDS[next_tier] - current_points)


@router.get("/balance", response_model=LoyaltyBalance)
def get_loyalty_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's loyalty points balance and tier"""
    # Calculate total points (earned - redeemed - expired)
    total_points = (
        db.query(func.coalesce(func.sum(LoyaltyPoint.points), 0))
        .filter(LoyaltyPoint.user_id == current_user.id)
        .scalar()
    )

    tier = get_tier(total_points)
    points_to_next = get_points_to_next_tier(total_points, tier)

    # Get recent history
    history = (
        db.query(LoyaltyPoint)
        .filter(LoyaltyPoint.user_id == current_user.id)
        .order_by(LoyaltyPoint.created_at.desc())
        .limit(20)
        .all()
    )

    return LoyaltyBalance(
        total_points=total_points,
        tier=tier,
        points_to_next_tier=points_to_next,
        history=history,  # type: ignore[arg-type]
    )


@router.get("/history", response_model=List[LoyaltyPointSchema])
def get_loyalty_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's loyalty points transaction history"""
    transactions = (
        db.query(LoyaltyPoint)
        .filter(LoyaltyPoint.user_id == current_user.id)
        .order_by(LoyaltyPoint.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return transactions


@router.post("/redeem", response_model=LoyaltyPointSchema)
def redeem_points(
    data: LoyaltyRedemption,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Redeem loyalty points for discount"""
    if data.points_to_redeem <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Points must be greater than 0"
        )

    # Check available balance
    total_points = (
        db.query(func.coalesce(func.sum(LoyaltyPoint.points), 0))
        .filter(LoyaltyPoint.user_id == current_user.id)
        .scalar()
    )

    if data.points_to_redeem > total_points:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient points. Available: {total_points}"
        )

    # Create redemption transaction
    redemption = LoyaltyPoint(
        user_id=current_user.id,
        points=-data.points_to_redeem,  # Negative for redemption
        transaction_type="redeemed",
        description=f"Redeemed {data.points_to_redeem} points for discount",
    )
    db.add(redemption)
    db.commit()
    db.refresh(redemption)
    return redemption


@router.get("/tier-benefits")
def get_tier_benefits():
    """Get benefits for each loyalty tier"""
    return {
        "bronze": {
            "discount_percentage": 0,
            "free_shipping_threshold": 100,
            "early_access": False,
            "exclusive_deals": False,
        },
        "silver": {
            "discount_percentage": 5,
            "free_shipping_threshold": 75,
            "early_access": False,
            "exclusive_deals": True,
        },
        "gold": {
            "discount_percentage": 10,
            "free_shipping_threshold": 50,
            "early_access": True,
            "exclusive_deals": True,
        },
        "platinum": {
            "discount_percentage": 15,
            "free_shipping_threshold": 0,
            "early_access": True,
            "exclusive_deals": True,
            "priority_support": True,
        },
    }


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.post("/admin/award", response_model=LoyaltyPointSchema)
def award_points(
    data: LoyaltyPointCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Award loyalty points to a user (admin only)"""
    # Verify user exists
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    transaction = LoyaltyPoint(**data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/admin/users/{user_id}", response_model=LoyaltyBalance)
def get_user_loyalty(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get a user's loyalty balance (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    total_points = (
        db.query(func.coalesce(func.sum(LoyaltyPoint.points), 0))
        .filter(LoyaltyPoint.user_id == user_id)
        .scalar()
    )

    tier = get_tier(total_points)
    points_to_next = get_points_to_next_tier(total_points, tier)

    history = (
        db.query(LoyaltyPoint)
        .filter(LoyaltyPoint.user_id == user_id)
        .order_by(LoyaltyPoint.created_at.desc())
        .limit(20)
        .all()
    )

    return LoyaltyBalance(
        total_points=total_points,
        tier=tier,
        points_to_next_tier=points_to_next,
        history=history,  # type: ignore[arg-type]
    )
