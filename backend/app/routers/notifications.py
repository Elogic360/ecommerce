"""
Notifications Router
User notification management and real-time push setup.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.customer import User
from app.models.features import Notification
from app.schemas.features import (
    Notification as NotificationSchema,
    NotificationCreate,
    NotificationList,
)
from app.core.security import get_current_user, get_current_admin_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList)
def get_notifications(
    unread_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's notifications"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    total = query.count()
    unread_count = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .scalar()
    )

    items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

    return NotificationList(items=items, unread_count=unread_count, total=total)  # type: ignore[arg-type]


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get count of unread notifications"""
    count = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .scalar()
    )
    return {"unread_count": count}


@router.patch("/{notification_id}/read", response_model=NotificationSchema)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()

    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    setattr(notification, 'is_read', True)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()

    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    db.delete(notification)
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all notifications for current user"""
    db.query(Notification).filter(Notification.user_id == current_user.id).delete()
    db.commit()


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.post("/admin/send", response_model=NotificationSchema, status_code=status.HTTP_201_CREATED)
def send_notification(
    data: NotificationCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Send a notification to a user (admin only)"""
    # Verify user exists
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    notification = Notification(**data.model_dump())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/admin/broadcast", status_code=status.HTTP_201_CREATED)
def broadcast_notification(
    title: str,
    message: str,
    notification_type: str = "announcement",
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Broadcast a notification to all active users (admin only)"""
    users = db.query(User).filter(User.is_active == True).all()

    notifications = [
        Notification(
            user_id=user.id,
            type=notification_type,
            title=title,
            message=message,
        )
        for user in users
    ]

    db.add_all(notifications)
    db.commit()

    return {"message": f"Notification sent to {len(notifications)} users"}
