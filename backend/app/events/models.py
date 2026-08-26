import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EventStatus(str, enum.Enum):
    EXTRACTED = "extracted"
    PENDING_VERIFICATION = "pending_verification"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class Event(Base):
    __tablename__ = "event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_extracted_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        Enum(
            EventStatus,
            name="event_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=EventStatus.EXTRACTED,
        index=True,
    )
    canonical_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("event.id"), nullable=True
    )
    moderator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
