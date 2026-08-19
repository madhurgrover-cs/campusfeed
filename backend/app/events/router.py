"""Events API: public read access plus moderator/admin manual creation."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.auth.models import UserRole
from app.core.database import get_db
from app.events.models import Event, EventStatus
from app.events.schemas import EventCreate, EventOut
from app.sources.models import Source

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)) -> list[Event]:
    return list(
        db.scalars(select(Event).where(Event.status == EventStatus.PUBLISHED))
    )


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: UUID, db: Session = Depends(get_db)) -> Event:
    event = db.scalar(
        select(Event).where(Event.id == event_id, Event.status == EventStatus.PUBLISHED)
    )
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.post(
    "",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))],
)
def create_event(payload: EventCreate, db: Session = Depends(get_db)) -> Event:
    source = db.get(Source, payload.source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source not found"
        )

    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
