# Track B (AI/Discovery Engine) -> Track A Integration Notes

## What this is

ai-engine/src/ contains the full discovery-and-intelligence pipeline: connectors
(website, image-based, PDF, news-mention), extraction, trust/sensitivity scoring,
deduplication, and change detection. See ai-engine/SAMPLE_OUTPUT.json for real
output examples produced by this pipeline.

## The core data shape

Defined in ai-engine/src/utils/schema.py (CAMPUS_ITEM_SCHEMA_PROMPT). Key points:

- item_type: event / announcement / opportunity / notice / achievement / deadline / other
- details: a FLEXIBLE object - please don't assume fixed columns for this. Different
  item types carry different keys (an event might have venue/prize_pool, an
  announcement might not).
- notable_attendees: array of strings, can be empty
- Canonical items (post-dedup) have a sources array - one campus item can have
  MULTIPLE linked sources.

## What I need from your side (backend/)

Since you've already built the moderation queue and Source model - could you confirm:
1. The exact endpoint path and expected request body for submitting a new item
2. Whether your Source model's fields line up with source_url/source_name/source_type
3. Auth requirements for this endpoint (does the AI engine need a service token?)

Once confirmed, I'll add a small adapter script that POSTs real output from
ai-engine/ into your actual API instead of just writing to local JSON files.

## Environment variables needed (see ai-engine/.env.example)

- GEMINI_API_KEY
- NEWSDATA_API_KEY
