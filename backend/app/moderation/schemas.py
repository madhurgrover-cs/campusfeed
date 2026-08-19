"""Request models for the moderation API."""

from pydantic import BaseModel


class ModerationDecision(BaseModel):
    note: str | None = None
