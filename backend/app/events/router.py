"""Events API: public read access plus moderator/admin manual creation."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.auth.models import UserRole
from app.core.database import get_db
from app.events.models import Event, EventStatus
from app.events.schemas import EventCreate, EventOut, PaginatedEvents
from app.sources.models import Source

router = APIRouter(prefix="/api/v1/events", tags=["events"])


def _paginate(query, db: Session, limit: int, offset: int) -> PaginatedEvents:
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    events = list(db.scalars(query.limit(limit).offset(offset)))
    return PaginatedEvents(total=total or 0, limit=limit, offset=offset, results=events)


@router.get("", response_model=PaginatedEvents)
def list_events(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedEvents:
    query = select(Event).where(Event.status == EventStatus.PUBLISHED)
    return _paginate(query, db, limit, offset)


@router.get("/search", response_model=PaginatedEvents)
def search_events(
    q: str | None = None,
    category: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedEvents:
    query = select(Event).where(Event.status == EventStatus.PUBLISHED)

    if q:
        pattern = f"%{q}%"
        query = query.where(or_(Event.title.ilike(pattern), Event.description.ilike(pattern)))
    if category:
        query = query.where(Event.event_type == category)
    if date_from:
        query = query.where(Event.start_at >= date_from)
    if date_to:
        query = query.where(Event.start_at <= date_to)

    return _paginate(query, db, limit, offset)


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
