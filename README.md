# veries-backend

Senior-style Python backend scaffold (FastAPI + `src/` layout).

## Quickstart

### 1) Install

```bash
python -m pip install -U pip
pip install -e ".[dev]"
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
