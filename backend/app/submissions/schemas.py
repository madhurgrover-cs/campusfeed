"""Request/response models for the submissions API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.submissions.models import SubmissionStatus


class SubmissionCreate(BaseModel):
    submitted_by: str
    raw_content: str


class SubmissionOut(BaseModel):
    id: UUID
    status: SubmissionStatus
    created_at: datetime

    model_config = {"from_attributes": True}
