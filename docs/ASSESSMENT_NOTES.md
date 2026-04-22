## Scope and intent

This backend is implemented to support an identity verification assessment with:
- Verification sessions + lifecycle status updates
- Upload association for ID image, selfie-with-ID, and background video
- Session event tracking for the interactive capture journey
- Optional BigQuery analytics export
- Optional cloud storage uploads (GCS)

## Persistence model (demo vs production)

The current implementation uses **in-memory repo implementations** for the domain:
- Sessions: `src/veries_backend/app/infra/verification_sessions_in_memory.py`
- Session events: `src/veries_backend/app/infra/verification_session_events_in_memory.py`
- Verification assets: `src/veries_backend/app/infra/verification_assets_in_memory.py`

This is intentionally suitable for local/demo flows only. Repo abstractions exist so you can swap in
durable implementations later without changing route/service contracts.

## Analytics tracking (BigQuery)

When enabled (`BIGQUERY_ENABLED=true`), the analytics sink attempts to write:
- Session upserts → `verification_sessions`
- Event appends → `verification_session_events`

Default behavior is best-effort (non-blocking writes, tolerated failures). Strict mode is available
via `BIGQUERY_FAIL_REQUESTS=true`.

## Upload storage (cloud)

Uploads are routed via `POST /api/verification-sessions/{session_id}/upload`.

- If `CLOUD_STORAGE_ENABLED=false` (default), files write to `UPLOAD_STORAGE_ROOT/<asset.storage_path>`.
- If `CLOUD_STORAGE_ENABLED=true`, files stream to GCS:
  - images → `GCS_BUCKET` under `GCS_IMAGES_PREFIX/<asset.storage_path>`
  - videos → `GCS_VIDEO_BUCKET` (or `GCS_BUCKET`) under `GCS_VIDEOS_PREFIX/<asset.storage_path>`

## Event integrity

To reduce reliance on the frontend, session creation and key status transitions automatically emit
deduped lifecycle events in `VerificationSessionsService`. Explicit frontend event logging remains
supported via `POST /api/verification-sessions/{id}/events`.

