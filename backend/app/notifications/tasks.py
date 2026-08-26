"""Background tasks that create notifications asynchronously."""

import uuid

from app.auth.models import User
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.notifications.models import Notification, NotificationChannel, NotificationPriority

_PRIORITY_RANK = {
    NotificationPriority.LOW: 0,
    NotificationPriority.MEDIUM: 1,
    NotificationPriority.HIGH: 2,
    NotificationPriority.CRITICAL: 3,
}


@celery_app.task(name="notifications.create_for_event_approval")
def create_notification_for_event_approval(
    user_id: str, event_id: str, title: str, body: str, priority: str
) -> str | None:
    """Create a Notification for user_id if it meets their min_priority preference."""

    db = SessionLocal()
    try:
        user = db.get(User, uuid.UUID(user_id))
        if user is None:
            return None

        priority_enum = NotificationPriority(priority)
        if _PRIORITY_RANK[priority_enum] < _PRIORITY_RANK[user.min_priority]:
            return None

        notification = Notification(
            user_id=user.id,
            event_id=uuid.UUID(event_id),
            title=title,
            body=body,
            priority=priority_enum,
            channel=NotificationChannel.IN_APP,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return str(notification.id)
    finally:
        db.close()
