# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CampusFeed is a backend service (FastAPI) that aggregates campus events from scraped sources and user
submissions, runs them through an extraction/verification pipeline, and publishes approved events. The
codebase is early-stage: only the data model and a health-check endpoint exist so far — no routers,
schemas, auth logic, or scraping/extraction code has been implemented yet.

## Commands

All commands run from `backend/` with a Python virtualenv active (repo has a `venv/` at the project root
that is gitignored — create your own if it doesn't exist).

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start local Postgres (from repo root)
docker compose up -d

# Run the API (from backend/)
uvicorn app.main:app --reload

# Apply migrations (from backend/)
alembic upgrade head

# Autogenerate a new migration after changing SQLAlchemy models (from backend/)
alembic revision --autogenerate -m "description"
```

No test suite, linter, or formatter is configured yet — `requirements.txt` only contains runtime
dependencies (fastapi, uvicorn, sqlalchemy, psycopg, alembic, pydantic-settings).

## Configuration

- Settings are loaded via `app/core/config.py` (`pydantic-settings`) from a `.env` file at the **repo
  root** (not `backend/.env`) — see `.env.example` for the required `DATABASE_URL` and the Postgres
  credentials used by `docker-compose.yml`.
- `DATABASE_URL` uses the `postgresql+psycopg://` driver (psycopg 3, not psycopg2).

## Architecture

The backend is organized as domain modules under `backend/app/`, each currently holding just a
`models.py`:

- `app/auth/` — `User` model with role-based access (`student` / `moderator` / `admin`).
- `app/sources/` — `Source` model: a scrapable origin (e.g. a campus website) events are extracted from.
- `app/events/` — `Event` model: the core entity. Events are extracted from a `Source`, carry a
  `raw_extracted_json` payload and `confidence_score` from the extraction step, move through a status
  lifecycle (`extracted` → `pending_verification` → `approved`/`rejected` → `published`), and can point
  to a `canonical_id` (a self-referential FK) for deduplicating near-identical events.
- `app/submissions/` — `Submission` model: raw user-submitted event text, which may later be linked to
  an extracted `Event` via `extracted_event_id` once processed.
- `app/core/` — shared infrastructure: `config.py` (Settings) and `database.py` (SQLAlchemy `Base`,
  `engine`, `SessionLocal`, and the `get_db` dependency for future route handlers).
- `app/main.py` — FastAPI app instance; currently exposes only `GET /health`, which checks DB
  connectivity.

All domain models inherit from the single `Base` in `app/core/database.py`, use UUID primary keys
(`uuid.uuid4` defaults), and represent enum-valued columns as Postgres native enums via SQLAlchemy's
`Enum(..., values_callable=...)` pattern (stores the enum's `.value`, not its name).

### Migrations

`alembic/env.py` imports every domain model module explicitly (`app.auth.models`, `app.events.models`,
`app.sources.models`, `app.submissions.models`) so `Base.metadata` is fully populated for autogeneration
— when adding a new domain module with its own models, add the corresponding import there or it will be
silently excluded from migrations. `env.py` also derives `sqlalchemy.url` from `app.core.config.Settings`
rather than reading it from `alembic.ini` (which has an empty `sqlalchemy.url`).
## Team Workflow — READ BEFORE STARTING ANY TASK

This is a two-person student project split into two tracks:
- **Track A (this person, "AM"):** backend API, database, auth, moderation
  queue/admin, notifications, deployment/infra.
- **Track B (teammate, separate work — not part of this session):**
  connectors/scraping, LLM extraction, deduplication, sensitivity scoring,
  newswire generation.

Only build Track A scope in this session unless explicitly told otherwise.
Do not create files under `app/connectors/`, `app/extraction/`,
`app/deduplication/`, or `app/newswire/` — that's teammate's work.

## Scope Discipline Rules

1. **Before writing any code**, list the exact files you plan to create or
   modify, and wait for confirmation if the task description is at all
   ambiguous.
2. **Implement only what's explicitly requested.** Do not add extra
   endpoints, fields, dependencies, or "while I'm here" improvements without
   asking first.
3. **Do not create modules/folders beyond what's asked**, even if they're
   part of the eventual roadmap (e.g. don't scaffold `notifications/` or
   `search/` unless the current task is specifically about them).
4. **Never modify unrelated files** without flagging it and asking first.
5. **Always confirm your working directory is D:\PROJECTS\campusfeed**
   before making changes, at the start of every session.
6. **After implementing:** run the app / relevant command yourself to
   confirm it actually works (don't just claim success — show the actual
   output, e.g. server starts cleanly, a test curl command succeeds,
   migration applies without error).
7. **Summarize what changed** at the end of every task, and flag anything
   that needs manual verification.
8. **No new dependencies** (libraries, services, infra like Redis/Celery/
   Docker changes) without explaining why the existing stack doesn't cover
   it, and getting confirmation first.
9. `verification/` (once it exists) is a shared module — Track A owns the
   moderation queue API and approve/reject workflow; Track B owns
   trust/confidence scoring and sensitivity classification. Flag before
   editing logic that isn't clearly your track's piece.

## Do Not Build Yet
Microservices, Kafka, Kubernetes, any vector/graph DB, automated trust
scoring, multi-university support, RAG/AI chat, OCR, notifications system,
Redis/Celery (until Phase 4 genuinely needs it), CI/CD, monitoring stack —
these are real future phases, not current tasks. Building them now without
being asked is scope creep.