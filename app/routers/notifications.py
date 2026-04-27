from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.notification import NotificationOut
from app.services.notification_service import (
    get_unread_notifications_for_user,
    mark_notification_as_read,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def get_unread_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_unread_notifications_for_user(db, user_id=current_user.id)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return mark_notification_as_read(
        db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
