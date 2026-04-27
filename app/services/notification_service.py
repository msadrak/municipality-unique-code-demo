from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.users import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    message: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        message=message.strip(),
        is_read=False,
    )
    db.add(notification)
    db.flush()
    return notification


def get_unread_notifications_for_user(
    db: Session,
    *,
    user_id: int,
) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )


def mark_notification_as_read(
    db: Session,
    *,
    notification_id: int,
    user_id: int,
) -> Notification:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
