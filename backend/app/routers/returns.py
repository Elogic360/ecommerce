"""
Returns Router
Return request management for orders.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.models.customer import User
from app.models.order import Order
from app.models.features import ReturnRequest
from app.schemas.features import (
    ReturnRequest as ReturnRequestSchema,
    ReturnRequestCreate,
    ReturnRequestUpdate,
)
from app.core.security import get_current_user, get_current_admin_user

router = APIRouter(prefix="/returns", tags=["returns"])


@router.get("", response_model=List[ReturnRequestSchema])
def get_my_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's return requests"""
    returns = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.user_id == current_user.id)
        .order_by(ReturnRequest.created_at.desc())
        .all()
    )
    return returns


@router.post("", response_model=ReturnRequestSchema, status_code=status.HTTP_201_CREATED)
def create_return_request(
    data: ReturnRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a return request for an order"""
    # Check order exists and belongs to user
    order = db.query(Order).filter(
        Order.id == data.order_id,
        Order.user_id == current_user.id,
    ).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Check order is delivered
    if order.status != "delivered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only request return for delivered orders"
        )

    # Check if return already exists
    existing = db.query(ReturnRequest).filter(
        ReturnRequest.order_id == data.order_id,
        ReturnRequest.status.in_(["pending", "approved"]),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return request already exists for this order"
        )

    return_request = ReturnRequest(
        order_id=data.order_id,
        user_id=current_user.id,
        reason=data.reason,
        description=data.description,
    )
    db.add(return_request)
    db.commit()
    db.refresh(return_request)
    return return_request


@router.get("/{return_id}", response_model=ReturnRequestSchema)
def get_return_request(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific return request"""
    return_request = db.query(ReturnRequest).filter(
        ReturnRequest.id == return_id,
        ReturnRequest.user_id == current_user.id,
    ).first()

    if not return_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")

    return return_request


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/all", response_model=List[ReturnRequestSchema])
def list_all_returns(
    status_filter: Optional[str] = Query(None, pattern="^(pending|approved|rejected|completed)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """List all return requests (admin only)"""
    query = db.query(ReturnRequest)
    if status_filter:
        query = query.filter(ReturnRequest.status == status_filter)

    return query.order_by(ReturnRequest.created_at.desc()).offset(skip).limit(limit).all()


@router.patch("/admin/{return_id}", response_model=ReturnRequestSchema)
def update_return_status(
    return_id: int,
    data: ReturnRequestUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Update return request status (admin only)"""
    return_request = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()

    if not return_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")

    update_data = data.model_dump(exclude_unset=True)

    if "status" in update_data:
        new_status = update_data["status"]
        if new_status in ["approved", "rejected"]:
            setattr(return_request, 'approved_by', current_admin.id)
            setattr(return_request, 'approved_at', datetime.utcnow())

    for field, value in update_data.items():
        setattr(return_request, field, value)

    db.commit()
    db.refresh(return_request)
    return return_request
