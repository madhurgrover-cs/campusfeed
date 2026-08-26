from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.auth.router import router as auth_router
from app.core.database import engine
from app.events.router import router as events_router
from app.ingest.router import router as ingest_router
from app.moderation.router import router as moderation_router
from app.notifications.router import router as notifications_router
from app.submissions.router import router as submissions_router

app = FastAPI(title="CampusFeed")
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(ingest_router)
app.include_router(moderation_router)
app.include_router(notifications_router)
app.include_router(submissions_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc

    return {"status": "ok", "database": "connected"}
