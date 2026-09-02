from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db, Business, Notification
from dependencies import get_current_business
from schemas import (
    NotificationOut,
    NotificationsListOut,
    UnreadCountOut,
    MessageOut,
)

router = APIRouter(prefix="/notifications", tags=["Business Notifications"])


@router.get("", response_model=NotificationsListOut)
def list_business_notifications(
    limit: int = 50,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieve all notifications for the current business."""
    notifications = db.query(Notification).filter(
        Notification.business_id == current_business.id
    ).order_by(Notification.created_at.desc()).limit(limit).all()

    unread_count = db.query(Notification).filter(
        Notification.business_id == current_business.id,
        Notification.is_read == False,
    ).count()

    return NotificationsListOut(
        total=len(notifications),
        unread_count=unread_count,
        notifications=notifications,
    )


@router.get("/unread-count", response_model=UnreadCountOut)
def get_business_unread_count(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Get count of unread notifications."""
    count = db.query(Notification).filter(
        Notification.business_id == current_business.id,
        Notification.is_read == False,
    ).count()

    return UnreadCountOut(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_as_read(
    notification_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Mark a specific notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.business_id == current_business.id,
    ).first()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found.",
        )

    notif.is_read = True
    notif.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/mark-all-read", response_model=MessageOut)
def mark_all_notifications_as_read(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        Notification.business_id == current_business.id,
        Notification.is_read == False,
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()

    return {"message": "All notifications marked as read."}
