import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    REJECTED = "rejected"


class Submission(Base):
    __tablename__ = "submission"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_by: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("event.id"), nullable=True
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(
            SubmissionStatus,
            name="submission_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=SubmissionStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
