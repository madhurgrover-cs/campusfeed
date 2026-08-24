"""AI-engine ingest API: batch intake for extracted campus items.

v0.1 policy (do not change without re-confirming with the team): regardless of
the item's upstream trust/sensitivity "decision" (AUTO_PUBLISH or
HOLD_FOR_HUMAN_REVIEW), every Event created here gets
status=pending_verification. decision/trust/sensitivity are stored as data
inside raw_extracted_json, never used to skip moderation.

Item shape: see app/ingest/schemas.py docstring - the request body is a raw
list[dict] because the upstream contract (ai-engine/) is explicitly flexible
and wasn't finalized when this was written. Fields are read defensively with
.get() so a differently-shaped item reports its own per-item error instead of
breaking the batch.
"""

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.events.models import Event, EventStatus
from app.ingest.auth import verify_ingest_token
from app.ingest.models import EventSource, IngestedItem, IngestedItemStatus
from app.ingest.schemas import IngestResultItem
from app.sources.models import Source, SourceType

router = APIRouter(
    prefix="/api/v1/ingest",
    tags=["ingest"],
    dependencies=[Depends(verify_ingest_token)],
)


def _parse_date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        if len(value) == 10:
            return datetime.combine(date.fromisoformat(value), datetime.min.time(), tzinfo=timezone.utc)
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _source_entries(item: dict[str, Any], primary_card: dict[str, Any]) -> list[dict[str, Any]]:
    sources = item.get("sources")
    if isinstance(sources, list) and sources:
        return [s for s in sources if isinstance(s, dict) and s.get("source_url")]
    if primary_card.get("source_url"):
        return [{
            "source_url": primary_card.get("source_url"),
            "source_name": primary_card.get("source_name"),
            "source_type": "web",
        }]
    return []


def _get_or_create_source(db: Session, url: str, name: str | None) -> Source:
    source = db.scalar(select(Source).where(Source.url == url))
    if source is not None:
        return source
    source = Source(name=name or url, url=url, source_type=SourceType.WEB)
    db.add(source)
    db.flush()
    return source


def _create_event(db: Session, item: dict[str, Any]) -> Event:
    primary_card = item.get("primary_card") or {}
    raw = primary_card.get("raw_extracted_data") or {}
    details = raw.get("details")
    trust = item.get("trust") or {}

    title = raw.get("title") or primary_card.get("headline")
    if not title:
        raise ValueError("item has no title (checked primary_card.raw_extracted_data.title and primary_card.headline)")

    entries = _source_entries(item, primary_card)
    if not entries:
        raise ValueError("item has no usable source information (checked sources[] and primary_card.source_url)")

    primary_url = primary_card.get("source_url") or entries[0].get("source_url")

    created: list[tuple[Source, str]] = []
    seen_source_ids: set[Any] = set()
    for entry in entries:
        url = entry.get("source_url")
        source = _get_or_create_source(db, url, entry.get("source_name"))
        if source.id in seen_source_ids:
            continue
        seen_source_ids.add(source.id)
        created.append((source, url))

    primary_source = next((s for s, url in created if url == primary_url), created[0][0])

    event = Event(
        source_id=primary_source.id,
        title=title,
        description=primary_card.get("one_liner"),
        event_type=raw.get("item_type") or item.get("item_type") or "event",
        venue=details.get("venue") if isinstance(details, dict) else None,
        start_at=_parse_date(raw.get("date_start")),
        end_at=_parse_date(raw.get("date_end")),
        source_url=primary_url or primary_source.url,
        image_url=primary_card.get("image_url"),
        raw_extracted_json=item,
        confidence_score=trust.get("trust_score"),
        status=EventStatus.PENDING_VERIFICATION,
    )
    db.add(event)
    db.flush()

    for source, url in created:
        role = "primary" if source.id == primary_source.id else "corroborating"
        db.add(EventSource(event_id=event.id, source_id=source.id, role=role, url=url))

    return event


def _process_item(db: Session, item: dict[str, Any]) -> IngestResultItem:
    if not isinstance(item, dict):
        return IngestResultItem(item_id=None, status="error", detail="item must be a JSON object")

    item_id = item.get("item_id")
    item_type = item.get("item_type")

    if not item_id or not isinstance(item_id, str):
        return IngestResultItem(item_id=None, status="error", detail="item_id is required")
    if not item_type or not isinstance(item_type, str):
        return IngestResultItem(item_id=item_id, status="error", detail="item_type is required")

    existing = db.scalar(select(IngestedItem).where(IngestedItem.item_id == item_id))
    if existing is not None:
        return IngestResultItem(
            item_id=item_id,
            status="duplicate",
            event_id=existing.event_id,
            detail="item_id already ingested, skipped (not overwritten)",
        )

    event_id = None
    ingested_status = IngestedItemStatus.RECEIVED
    detail = None

    if item_type == "event":
        try:
            event = _create_event(db, item)
            event_id = event.id
            ingested_status = IngestedItemStatus.PROJECTED
        except Exception as exc:
            db.rollback()
            ingested_status = IngestedItemStatus.SKIPPED
            detail = f"could not construct Event, item preserved as skipped: {exc}"

    ingested_item = IngestedItem(
        item_id=item_id,
        item_type=item_type,
        payload=item,
        status=ingested_status,
        event_id=event_id,
    )
    db.add(ingested_item)
    db.commit()

    return IngestResultItem(item_id=item_id, status=ingested_status.value, event_id=event_id, detail=detail)


@router.post("", response_model=list[IngestResultItem])
def ingest_batch(items: list[dict[str, Any]], db: Session = Depends(get_db)) -> list[IngestResultItem]:
    return [_process_item(db, item) for item in items]
