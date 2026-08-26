"""Response models for the /ingest API.

The request body is intentionally untyped (list[dict]) rather than a strict
Pydantic model. The item shape is confirmed against
ai-engine/src/pipeline/build_ingest_payload.py on the track-b branch (see the
module docstring in app/ingest/router.py for the full shape), but "details" in
particular is explicitly flexible per ai-engine/INTEGRATION_NOTES.md, and this
whole contract has already changed once since this endpoint was first written.
Validation of what's actually needed is done defensively per-item in the
router so one malformed item reports its own error status instead of
rejecting or crashing the whole batch.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class IngestResultItem(BaseModel):
    """Per-item ingest outcome.

    status meanings:
    - projected: new event-type item, an Event row was created (always pending_verification).
    - received: new non-event item, stored in ingested_items only, no Event row.
    - skipped: new event-type item whose Event could not be constructed (e.g. missing
      title/source); the raw payload is still stored in ingested_items for later review.
    - duplicate: item_id already existed, skipped - no row inserted, nothing overwritten.
    - error: the envelope itself was invalid (missing item_id/item_type), so it could not
      even be recorded in ingested_items (item_id is the table's unique/not-null key).
    """

    item_id: str | None
    status: Literal["projected", "received", "skipped", "duplicate", "error"]
    event_id: UUID | None = None
    detail: str | None = None
