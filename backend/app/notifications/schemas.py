"""Response models for the notifications API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.notifications.models import NotificationChannel, NotificationPriority


class NotificationOut(BaseModel):
    id: UUID
    event_id: UUID | None
    title: str
    body: str
    priority: NotificationPriority
    channel: NotificationChannel
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
