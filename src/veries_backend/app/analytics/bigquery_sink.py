from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from veries_backend.app.analytics.sink import AnalyticsSink
from veries_backend.app.core.config import Settings
from veries_backend.app.domain.verification_sessions.events import VerificationSessionEvent
from veries_backend.app.domain.verification_sessions.model import VerificationSession


def _dt_to_iso(dt: datetime) -> str:
    return dt.isoformat()


class BigQueryAnalyticsSink(AnalyticsSink):
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings
        self._client = self._create_client()

    def _create_client(self):
        from google.cloud import bigquery  # type: ignore[import-not-found]

        if self._settings.bigquery_credentials_path:
            return bigquery.Client.from_service_account_json(
                self._settings.bigquery_credentials_path,
                project=self._settings.bigquery_project,
            )
        return bigquery.Client(project=self._settings.bigquery_project)

    def upsert_verification_session(self, session: VerificationSession) -> None:
        table = self._table_id(self._settings.bigquery_sessions_table)
        row = {
            "session_id": str(session.id),
            "status": session.status.value,
            "client_reference": session.client_reference,
            "metadata": session.metadata,
            "created_at": _dt_to_iso(session.created_at),
            "updated_at": _dt_to_iso(session.updated_at),
        }
        self._insert_json_rows(table, [row])

    def append_verification_session_event(self, event: VerificationSessionEvent) -> None:
        table = self._table_id(self._settings.bigquery_events_table)
        row = {
            "event_id": str(event.id),
            "session_id": str(event.session_id),
            "event_type": event.event_type.value,
            "occurred_at": _dt_to_iso(event.occurred_at),
            "received_at": _dt_to_iso(event.received_at),
            "metadata": event.metadata,
        }
        self._insert_json_rows(table, [row])

    def _table_id(self, table: str) -> str:
        if not self._settings.bigquery_dataset:
            raise RuntimeError("BIGQUERY_DATASET is required when BIGQUERY_ENABLED=true")
        project = self._settings.bigquery_project or self._client.project
        return f"{project}.{self._settings.bigquery_dataset}.{table}"

    def _insert_json_rows(self, table_id: str, rows: list[dict[str, Any]]) -> None:
        try:
            errors = self._client.insert_rows_json(table_id, rows)
        except TypeError:
            safe_rows = json.loads(json.dumps(rows, default=str))
            errors = self._client.insert_rows_json(table_id, safe_rows)
        if errors:
            raise RuntimeError(f"BigQuery insert failed for {table_id}: {errors}")
