# Project write-up (backend): Identity Verification UX Enhancement

This repository is a FastAPI backend that supports the “Identity Verification UX Enhancement”
assessment flow described in `Frontend Engineer - Assessment  .pdf`.

## What I built

- **Verification sessions** with a simple lifecycle (`started → in_progress → submitted → completed`,
  plus `dropped_off/resumed/failed`): `POST/GET/PATCH /api/verification-sessions/{id}`.
- **Event tracking** for the interactive capture journey:
  - `POST /api/verification-sessions/{id}/events` (client-driven events)
  - `GET /api/verification-sessions/{id}/events` (readback)
  - Automatic, deduped **server-emitted lifecycle events** on key transitions.
- **Upload pipeline** compatible with the “existing upload API” idea:
  - `POST /api/verification-sessions/{id}/upload` accepts `customer_id`, `asset_type`, and a file.
  - `asset_type` supports `id_document`, `selfie_with_id`, and `background_video`.
  - Uploads validate **content-type** and enforce **max size** limits (separate limits for images vs
    video).
- **Asset association** so uploads are stored and retrievable per session:
  - `POST/GET /api/verification-sessions/{id}/assets`
  - `PATCH /api/verification-assets/{asset_id}`
- **Optional analytics export to BigQuery** (bonus requirement): when enabled, sessions/events are
  written to BigQuery tables in a best-effort, non-blocking way.
- **Optional cloud storage uploads (GCS)** (bonus requirement): the same upload flow can write to
  local disk (default) or to Google Cloud Storage.

## Why I chose this construction method

- **`src/` layout + modular packaging**: keeps the app importable/testable and avoids path hacks.
- **Clean separation of concerns**:
  - `domain/`: models + enums (business concepts)
  - `services/`: use-cases (workflow rules: transitions, uploads, tracking)
  - `infra/`: repository implementations (in-memory for demo)
  - `api/`: FastAPI routers + request/response schemas
  - `storage/` + `analytics/`: pluggable integrations (local/GCS, NoOp/BigQuery)
- **Dependency inversion + DI** via FastAPI dependencies (`app/deps.py`): makes it easy to swap
  in durable persistence later and makes tests straightforward (dependency overrides).
- **Assessment-friendly defaults**: optional integrations (BigQuery/GCS) are *opt-in* and designed to
  fail gracefully so the core verification flow works in local/demo environments.

## Principles I applied (and where they show up)

- **Single Responsibility**: uploads, events, sessions, analytics, and storage are separate modules.
- **Explicit state machine**: session status transitions are validated to prevent invalid jumps; invalid
  transitions return `409` (conflict). (`services/verification_sessions.py`)
- **Defensive input handling**:
  - Storage paths are generated from safe segments (prevents path traversal).
  - MIME types are validated per asset type.
  - Upload size limits prevent accidental resource exhaustion. (`services/uploads.py`)
- **Observability / auditability**: key steps produce structured events; optionally persisted to BigQuery.
- **Testability**: the `tests/` suite exercises session lifecycle, event logging, and uploads.

## How this backend aligns with the assessment PDF

### 1) Compatibility with existing upload infrastructure

The assessment says the current flow uploads two images to an existing upload API and stores them
via the backend. This backend keeps that shape but generalizes it:

- `POST /api/verification-sessions/{session_id}/upload` supports:
  - `id_document` image (and PDF)
  - `selfie_with_id` image
  - `background_video` video (bonus)

Implementation:
- Route: `src/veries_backend/app/api/routes/uploads.py`
- Upload orchestration: `src/veries_backend/app/services/uploads.py`
- Storage abstraction (local/GCS): `src/veries_backend/app/storage/`

### 2) Tracking events in the interactive capture session (bonus)

The assessment asks for progress tracking events (start, drop-off, resumption) stored in BigQuery.
This backend supports both client-driven and server-driven tracking:

- Client-driven events: `POST /api/verification-sessions/{id}/events`
  - Supports event types like `camera_opened`, `mode_switched`, `capture_taken`, `capture_retaken`.
  - Enum: `src/veries_backend/app/domain/verification_sessions/events.py`
- Server-driven lifecycle events (deduped):
  - create session ⇒ emits `session_started`
  - patch status to `dropped_off` ⇒ emits `drop_off`
  - patch status to `resumed` ⇒ emits `resume`
  - patch status to `submitted` ⇒ emits `submission_confirmed`
  - patch status to `completed` ⇒ emits `completed`

Implementation:
- Lifecycle emission + status transition rules: `src/veries_backend/app/services/verification_sessions.py`
- Event logging service: `src/veries_backend/app/services/verification_session_events.py`
- Optional BigQuery sink: `src/veries_backend/app/analytics/bigquery_sink.py`

### 3) Background recording upload (bonus)

The assessment’s bonus requires a background video that starts with the verification flow and is
uploaded alongside images.

This backend supports receiving that video as a normal upload:
- `asset_type=background_video`
- Video MIME types: `video/mp4`, `video/quicktime`, `video/webm`
- Separate size limit (`MAX_VIDEO_UPLOAD_BYTES`)
- Optional routing to a dedicated bucket/prefix:
  - `GCS_VIDEO_BUCKET` (falls back to `GCS_BUCKET`)
  - `GCS_VIDEOS_PREFIX`

Implementation:
- Type: `src/veries_backend/app/domain/verification_assets/types.py`
- Validation + bucket routing: `src/veries_backend/app/services/uploads.py`
- Settings + wiring: `src/veries_backend/app/core/config.py`, `src/veries_backend/app/deps.py`

## What I intentionally left “swappable” for production

- **Durable persistence**: repositories are in-memory to keep the assessment runnable anywhere, but
  repo interfaces exist so a DB implementation can be added without changing API contracts.
- **AuthN/AuthZ**: not required by the prompt; in production, these endpoints would be protected and
  storage buckets locked down accordingly.

## Quick verification

- Run dev server: `make dev` then `GET http://localhost:8000/api/health`
- Run tests: `make test`

