import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.notifications.models import NotificationPriority


class UserRole(str, enum.Enum):
    STUDENT = "student"
    MODERATOR = "moderator"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=UserRole.STUDENT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    min_priority: Mapped[NotificationPriority] = mapped_column(
        Enum(
            NotificationPriority,
            name="notification_priority",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=NotificationPriority.LOW,
        server_default=NotificationPriority.LOW.value,
    )
