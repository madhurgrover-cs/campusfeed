"""Submissions API: public intake and status lookup."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.submissions.models import Submission
from app.submissions.schemas import SubmissionCreate, SubmissionOut

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(payload: SubmissionCreate, db: Session = Depends(get_db)) -> Submission:
    submission = Submission(
        submitted_by=payload.submitted_by,
        raw_content=payload.raw_content,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: UUID, db: Session = Depends(get_db)) -> Submission:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    return submission
