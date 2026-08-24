# Track B (AI/Discovery Engine) -> Track A Integration Notes

## What this is
ai-engine/src/ contains the discovery-and-intelligence pipeline: connectors
(static HTML, image-based, PDF, news-mention), extraction, trust/sensitivity
scoring, deduplication, and change detection.

## The ingest payload
`ai-engine/SAMPLE_OUTPUT.json` is a real payload, produced end-to-end by
`run_pipeline_test.py`. Build against this, not against the extraction schema
alone - the payload is assembled from three stages (connector card, dedup
canonical item, validation result) by `src/pipeline/build_ingest_payload.py`.

Top-level fields:
- `item_id` - 16-char SHA-256 of source_url. Use as the idempotency key for
  upsert. Keyed on URL, not content, so it is stable across content changes.
- `schema_version` - currently "0.1".
- `item_type` - lifted to top level for routing. Only `event` creates an Event
  row in v0.1; everything else lands in `ingested_items`.
- `card` - display object: headline, one_liner, category_emoji, source_tag,
  image_url. Note image_url still needs a real column on your side.
- `extracted` - the full CampusItem (see src/utils/schema.py).
- `sources[]` - one entry per distinct source_url. Deduped on append.
- `trust` / `sensitivity` - separate objects, deliberately not blended.
- `decision` / `requires_review` - already derived; no need to compute these.

## Item type rules
- Something happening (fest, workshop, competition) -> `event`
- A cutoff with no happening (scholarship closes Friday) -> `deadline`
- Both -> `event`, with the cutoff at `details.registration_deadline`
- Uncertain between the two -> `event` (a wrong event is visible and fixable in
  the moderation queue; a wrong deadline is invisible)

## Still flexible - do not add fixed columns
`details` is a FLEXIBLE object. Different item types carry different keys (an
event may have venue/prize_pool, an announcement may not). Do not assume a
fixed set.

## Known behaviour worth agreeing on
On duplicate detection, dedup keeps the existing item and only appends to
`sources[]` - the newer extraction is discarded. So re-ingesting the same URL
does not currently improve stored content. change_detection is the intended
path for updates. Open question: should a repeat POST to /ingest overwrite?

## Environment variables (see ai-engine/.env.example)
- GEMINI_API_KEY
- NEWSDATA_API_KEY (news connector only; currently paused)
