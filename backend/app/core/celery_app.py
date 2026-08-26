"""Celery application instance for background job processing."""

from celery import Celery

from app.core.config import get_settings

# Import every domain model so Base.metadata is fully populated in the worker
# process before any task touches the ORM - mirrors alembic/env.py, which needs
# the same thing for FK resolution across tables (e.g. notification -> event).
import app.auth.models  # noqa: F401
import app.events.models  # noqa: F401
import app.ingest.models  # noqa: F401
import app.notifications.models  # noqa: F401
import app.sources.models  # noqa: F401
import app.submissions.models  # noqa: F401

celery_app = Celery(
    "campusfeed",
    broker=get_settings().redis_url,
    backend=get_settings().redis_url,
    include=["app.notifications.tasks"],
)
