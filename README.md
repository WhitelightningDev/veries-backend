# veries-backend

Senior-style Python backend scaffold (FastAPI + `src/` layout).

## Quickstart

### 1) Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

### 2) Configure env

```bash
cp .env.example .env
```

### 3) Run

```bash
make dev
```

Open:
- `GET http://localhost:8000/api/health`

If your frontend runs in the browser, set `CORS_ORIGINS` in `.env` (comma-separated) e.g.
`http://localhost:3000,http://localhost:5173`.

## Implementation notes (assessment-oriented)

### Repo abstraction + demo persistence

This codebase keeps a repo/service/domain split. For local/demo flows, it uses **in-memory**
repo implementations:
- Sessions: `src/veries_backend/app/infra/verification_sessions_in_memory.py`
- Session events: `src/veries_backend/app/infra/verification_session_events_in_memory.py`
- Verification assets: `src/veries_backend/app/infra/verification_assets_in_memory.py`

These are intentionally non-durable (state resets on process restart). The repo protocols live in:
- `src/veries_backend/app/domain/verification_sessions/repo.py`
- `src/veries_backend/app/domain/verification_sessions/events_repo.py`
- `src/veries_backend/app/domain/verification_assets/repo.py`

### Analytics (BigQuery)

Session and event analytics can be written to BigQuery via:
- `src/veries_backend/app/analytics/bigquery_sink.py`

For assessment delivery, the intended approach is:
- Use **BigQuery for analytics tracking** (sessions + events)
- Keep core verification flow tolerant if BigQuery is unavailable (best-effort by default)

See “BigQuery (optional analytics)” below for required tables and config.

### Uploads (cloud storage)

Uploads are handled by:
- `POST /api/verification-sessions/{session_id}/upload`

The upload pipeline persists a `VerificationAsset` record (id_document, selfie_with_id, background_video)
and stores the file in either:
- Local disk under `UPLOAD_STORAGE_ROOT` (demo/default)
- Google Cloud Storage when `CLOUD_STORAGE_ENABLED=true`

Background video can be routed to a separate bucket/prefix via:
- `GCS_VIDEO_BUCKET`
- `GCS_VIDEOS_PREFIX`

### Event integrity (reduced frontend burden)

Session status changes automatically emit best-effort lifecycle events server-side (deduped):
- create session → `session_started`
- status → `drop_off`, `resume`, `submission_confirmed`, `completed`

Explicit frontend logging via `POST /api/verification-sessions/{id}/events` remains supported
for richer metadata.
You can fetch recorded events via `GET /api/verification-sessions/{id}/events`.

## Tests

```bash
make test
```

## Lint / format

```bash
make lint
make format
```

## BigQuery (optional analytics)

This backend can write verification session state and session events to BigQuery via
`src/veries_backend/app/analytics/bigquery_sink.py`.

### Install deps

```bash
pip install -e ".[gcp]"
```

### Required env

Set in `.env`:
- `BIGQUERY_ENABLED=true`
- `BIGQUERY_DATASET=<dataset>`
- optionally: `BIGQUERY_PROJECT`, `BIGQUERY_CREDENTIALS_PATH`

Startup validation is controlled by:
- `BIGQUERY_VALIDATE_ON_STARTUP` (default `true`)
- `BIGQUERY_AUTOCREATE_TABLES` (default `false`)

### Expected tables

1) `verification_sessions`
- `session_id` STRING
- `status` STRING
- `client_reference` STRING (NULLABLE ok)
- `metadata` JSON (preferred) or STRING
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

2) `verification_session_events`
- `event_id` STRING
- `session_id` STRING
- `event_type` STRING
- `occurred_at` TIMESTAMP
- `received_at` TIMESTAMP
- `metadata` JSON (preferred) or STRING

### Error behavior

By default BigQuery writes are **best-effort** (non-blocking + tolerated failures):
- `BIGQUERY_ASYNC_WRITES=true`
- `BIGQUERY_FAIL_REQUESTS=false`

For strict behavior (fail requests on BigQuery errors), set:
- `BIGQUERY_FAIL_REQUESTS=true`
- `BIGQUERY_ASYNC_WRITES=false`

## Cloud storage (optional uploads)

Uploads can be stored in Google Cloud Storage via `src/veries_backend/app/storage/gcs.py`.

### Install deps

```bash
pip install -e ".[gcp]"
```

### Required env

Set in `.env`:
- `CLOUD_STORAGE_ENABLED=true`
- `GCS_BUCKET=<images bucket>`
- optionally: `GCS_VIDEO_BUCKET=<video bucket>`, `GCS_PROJECT`, `GCS_CREDENTIALS_PATH`

### Cloud Run (recommended: Service Account Identity)

On Cloud Run you typically **do not** use a JSON key file. Leave `GCS_CREDENTIALS_PATH` empty and
grant the Cloud Run runtime service account permission on your bucket(s) (e.g. `roles/storage.objectAdmin`).

By default, the object name is:
- images: `GCS_IMAGES_PREFIX/<asset.storage_path>`
- videos: `GCS_VIDEOS_PREFIX/<asset.storage_path>`
