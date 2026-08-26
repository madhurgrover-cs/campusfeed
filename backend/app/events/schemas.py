"""Request/response models for the events API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.events.models import EventStatus


class EventCreate(BaseModel):
    source_id: UUID
    title: str
    description: str | None = None
    event_type: str
    venue: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    registration_deadline: datetime | None = None
    source_url: str
    image_url: str | None = None
    status: EventStatus = EventStatus.PUBLISHED


class EventOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    event_type: str
    venue: str | None
    start_at: datetime | None
    end_at: datetime | None
    registration_deadline: datetime | None
    source_url: str
    image_url: str | None
    status: EventStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedEvents(BaseModel):
    total: int
    limit: int
    offset: int
    results: list[EventOut]
