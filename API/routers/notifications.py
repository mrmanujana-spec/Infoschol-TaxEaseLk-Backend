import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
try:
    from ..database import get_db, Business, Notification
    from ..auth import get_current_business
    from ..schemas import NotificationsListOut, NotificationOut, UnreadCountOut
except ImportError:
    from database import get_db, Business, Notification
    from auth import get_current_business
    from schemas import NotificationsListOut, NotificationOut, UnreadCountOut

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationsListOut)
def get_notifications(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    notifs = (
        db.query(Notification)
        .filter(Notification.business_id == current_business.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    unread = sum(1 for n in notifs if not n.is_read)
    return NotificationsListOut(total=len(notifs), unread_count=unread, notifications=notifs)


@router.get("/unread-count", response_model=UnreadCountOut)
def get_unread_count(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    count = db.query(Notification).filter(
        Notification.business_id == current_business.id,
        Notification.is_read == False,
    ).count()
    return UnreadCountOut(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_as_read(
    notification_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.business_id == current_business.id,
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found.")

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = datetime.utcnow()
        db.commit()
        db.refresh(notif)
    return notif