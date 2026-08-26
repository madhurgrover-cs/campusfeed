"""Moderation queue API: list pending events and approve/reject them."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User, UserRole
from app.core.database import get_db
from app.events.models import Event, EventStatus
from app.events.schemas import EventOut
from app.moderation.schemas import ModerationDecision
from app.notifications.models import NotificationPriority
from app.notifications.tasks import create_notification_for_event_approval

router = APIRouter(
    prefix="/api/v1/moderation",
    tags=["moderation"],
    dependencies=[Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))],
)


def _get_pending_event(event_id: UUID, db: Session) -> Event:
    event = db.scalar(
        select(Event).where(
            Event.id == event_id, Event.status == EventStatus.PENDING_VERIFICATION
        )
    )
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.get("/queue", response_model=list[EventOut])
def list_queue(db: Session = Depends(get_db)) -> list[Event]:
    return list(
        db.scalars(select(Event).where(Event.status == EventStatus.PENDING_VERIFICATION))
    )


@router.post("/{event_id}/approve", response_model=EventOut)
def approve_event(
    event_id: UUID,
    payload: ModerationDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Event:
    event = _get_pending_event(event_id, db)
    event.status = EventStatus.PUBLISHED
    event.moderator_note = payload.note
    db.commit()
    db.refresh(event)

    create_notification_for_event_approval.delay(
        user_id=str(current_user.id),
        event_id=str(event.id),
        title="Event published",
        body=f'"{event.title}" was approved and published.',
        priority=NotificationPriority.MEDIUM.value,
    )

    return event


@router.post("/{event_id}/reject", response_model=EventOut)
def reject_event(
    event_id: UUID, payload: ModerationDecision, db: Session = Depends(get_db)
) -> Event:
    event = _get_pending_event(event_id, db)
    event.status = EventStatus.REJECTED
    event.moderator_note = payload.note
    db.commit()
    db.refresh(event)
    return event
