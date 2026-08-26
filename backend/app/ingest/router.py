"""AI-engine ingest API: batch intake for extracted campus items.

v0.1 policy (do not change without re-confirming with the team): regardless of
the item's upstream trust/sensitivity "decision" (AUTO_PUBLISH or
HOLD_FOR_HUMAN_REVIEW) or the "requires_review" boolean, every Event created
here gets status=pending_verification. decision/trust/sensitivity/
requires_review are stored as data inside raw_extracted_json, NEVER read for
control flow - do not add an `if requires_review` shortcut here.

Item shape: confirmed against ai-engine/src/pipeline/build_ingest_payload.py
on the track-b branch (the real assembly step), as of its build_ingest_payload():

    {
      "item_id": str | None,          # sha256(source_url)[:16], via utils/cache.py
      "schema_version": "0.1",
      "item_type": str,               # == extracted["item_type"]
      "card": {
        "headline": str, "one_liner": str, "category_emoji": str,
        "source_tag": str, "image_url": str | None,
      },                               # NOTE: no source_url/source_name here
      "extracted": {                  # utils/schema.py CAMPUS_ITEM_SCHEMA_PROMPT shape
        "title": str, "item_type": str, "organizer": str, "department": str | None,
        "category": str, "date_start": str | None, "date_end": str | None,
        "details": dict, "notable_attendees": list[str], "tags": list[str],
        "confidence_notes": str,
      },
      "sources": [{"source_url": str, "source_name": str, "source_type": str}, ...],
      "trust": {"trust_score": int, "trust_label": str, "trust_reasons": list[str]},
      "sensitivity": {"sensitivity_level": str, "reason": str},
      "decision": "AUTO_PUBLISH" | "HOLD_FOR_HUMAN_REVIEW",
      "requires_review": bool,        # decision == HOLD_FOR_HUMAN_REVIEW, data only
      "connector_type": str,
    }

source_url/source_name live ONLY in sources[] (not on "card"), so the primary
source is taken as sources[0] (dedup.py appends corroborating sources after the
originating one). The request body is still typed as a raw list[dict] rather
than a strict Pydantic model, so a differently-shaped item reports its own
per-item error instead of breaking the batch - this contract can still drift.
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


def _get_or_create_source(db: Session, url: str, name: str | None) -> Source:
    source = db.scalar(select(Source).where(Source.url == url))
    if source is not None:
        return source
    source = Source(name=name or url, url=url, source_type=SourceType.WEB)
    db.add(source)
    db.flush()
    return source


def _create_event(db: Session, item: dict[str, Any]) -> Event:
    card = item.get("card") or {}
    extracted = item.get("extracted") or {}
    details = extracted.get("details")
    trust = item.get("trust") or {}

    title = extracted.get("title") or card.get("headline")
    if not title:
        raise ValueError("item has no title (checked extracted.title and card.headline)")

    entries = item.get("sources")
    entries = [s for s in entries if isinstance(s, dict) and s.get("source_url")] if isinstance(entries, list) else []
    if not entries:
        raise ValueError("item has no usable source information (sources[] is empty)")

    created: list[tuple[Source, str]] = []
    seen_source_ids: set[Any] = set()
    for entry in entries:
        url = entry.get("source_url")
        source = _get_or_create_source(db, url, entry.get("source_name"))
        if source.id in seen_source_ids:
            continue
        seen_source_ids.add(source.id)
        created.append((source, url))

    # sources[0] is the originating source (dedup.py appends merged/corroborating
    # sources after it) - there's no source_url on "card" to cross-check against.
    primary_source, primary_url = created[0]

    event = Event(
        source_id=primary_source.id,
        title=title,
        description=card.get("one_liner"),
        event_type=extracted.get("item_type") or item.get("item_type") or "event",
        venue=details.get("venue") if isinstance(details, dict) else None,
        start_at=_parse_date(extracted.get("date_start")),
        end_at=_parse_date(extracted.get("date_end")),
        source_url=primary_url,
        image_url=card.get("image_url"),
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
