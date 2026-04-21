from __future__ import annotations

import json
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from veries_backend.app.analytics.sink import AnalyticsSink
from veries_backend.app.core.config import Settings
from veries_backend.app.domain.verification_sessions.events import VerificationSessionEvent
from veries_backend.app.domain.verification_sessions.model import VerificationSession

logger = logging.getLogger("veries_backend.analytics.bigquery")


def _dt_to_iso(dt: datetime) -> str:
    return dt.isoformat()


@dataclass(frozen=True, slots=True)
class TableSchemaExpectation:
    table: str
    required_fields: dict[str, set[str]]
    # field name -> allowed types (e.g. {"metadata": {"JSON", "STRING"}})


_SESSIONS_EXPECTATION = TableSchemaExpectation(
    table="verification_sessions",
    required_fields={
        "session_id": {"STRING"},
        "status": {"STRING"},
        "client_reference": {"STRING"},
        "metadata": {"JSON", "STRING"},
        "created_at": {"TIMESTAMP", "DATETIME", "STRING"},
        "updated_at": {"TIMESTAMP", "DATETIME", "STRING"},
    },
)

_EVENTS_EXPECTATION = TableSchemaExpectation(
    table="verification_session_events",
    required_fields={
        "event_id": {"STRING"},
        "session_id": {"STRING"},
        "event_type": {"STRING"},
        "occurred_at": {"TIMESTAMP", "DATETIME", "STRING"},
        "received_at": {"TIMESTAMP", "DATETIME", "STRING"},
        "metadata": {"JSON", "STRING"},
    },
)


class BigQueryAnalyticsSink(AnalyticsSink):
    """
    Best-effort analytics sink.

    Default behavior is assessment-safe:
    - writes are async (non-blocking)
    - failures are logged and tolerated (do not fail requests)
    - optional startup validation can confirm table/schema readiness
    """

    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings
        self._configured, self._config_error = self._validate_settings(settings)

        self._client = None
        self._executor: ThreadPoolExecutor | None = None

        if not self._configured:
            logger.warning("BigQuery disabled (misconfigured): %s", self._config_error)
            return

        self._client = self._create_client()

        if settings.bigquery_fail_requests:
            if settings.bigquery_async_writes:
                logger.warning(
                    "BIGQUERY_FAIL_REQUESTS=true implies sync writes; forcing "
                    "BIGQUERY_ASYNC_WRITES=false"
                )
            self._async = False
        else:
            self._async = settings.bigquery_async_writes

        if self._async:
            self._executor = ThreadPoolExecutor(
                max_workers=max(1, int(settings.bigquery_async_max_workers)),
                thread_name_prefix="bigquery-analytics",
            )

        self._sessions_table = self._table_id(settings.bigquery_sessions_table)
        self._events_table = self._table_id(settings.bigquery_events_table)

        self._sessions_metadata_type: str | None = None
        self._events_metadata_type: str | None = None

    @staticmethod
    def _validate_settings(settings: Settings) -> tuple[bool, str | None]:
        if not settings.bigquery_dataset:
            return False, "BIGQUERY_DATASET is required"
        if not settings.bigquery_sessions_table:
            return False, "BIGQUERY_SESSIONS_TABLE is required"
        if not settings.bigquery_events_table:
            return False, "BIGQUERY_EVENTS_TABLE is required"
        return True, None

    def _create_client(self):
        from google.cloud import bigquery  # type: ignore[import-not-found]

        if self._settings.bigquery_credentials_path:
            return bigquery.Client.from_service_account_json(
                self._settings.bigquery_credentials_path,
                project=self._settings.bigquery_project,
            )
        return bigquery.Client(project=self._settings.bigquery_project)

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=False)
            self._executor = None

    def validate_on_startup(self) -> None:
        """
        Verifies required tables exist and contain required columns/types.

        - If BIGQUERY_AUTOCREATE_TABLES=true, attempts to create missing dataset/tables.
        - If BIGQUERY_FAIL_REQUESTS=true, raises on validation failures.
        - Otherwise logs warnings and continues.
        """
        if not self._configured or self._client is None:
            return

        try:
            if self._settings.bigquery_autocreate_tables:
                self._ensure_dataset()
                self._ensure_table(self._sessions_table, expectation=_SESSIONS_EXPECTATION)
                self._ensure_table(self._events_table, expectation=_EVENTS_EXPECTATION)

            self._validate_table_schema(self._sessions_table, expectation=_SESSIONS_EXPECTATION)
            self._validate_table_schema(self._events_table, expectation=_EVENTS_EXPECTATION)
            self._cache_metadata_types()
        except Exception as exc:
            if self._settings.bigquery_fail_requests:
                raise
            logger.warning("BigQuery validation failed (continuing): %s", exc)

    def _cache_metadata_types(self) -> None:
        if self._client is None:
            return
        sessions_table = self._client.get_table(self._sessions_table)
        events_table = self._client.get_table(self._events_table)
        self._sessions_metadata_type = _schema_field_type(sessions_table.schema, "metadata")
        self._events_metadata_type = _schema_field_type(events_table.schema, "metadata")

    def upsert_verification_session(self, session: VerificationSession) -> None:
        if not self._configured or self._client is None:
            return

        row = {
            "session_id": str(session.id),
            "status": session.status.value,
            "client_reference": session.client_reference,
            "metadata": session.metadata,
            "created_at": _dt_to_iso(session.created_at),
            "updated_at": _dt_to_iso(session.updated_at),
        }

        mode = (self._settings.bigquery_session_write_mode or "merge").lower().strip()
        if mode not in {"merge", "append"}:
            mode = "merge"

        if mode == "append":
            self._submit(
                lambda: self._insert_rows(self._sessions_table, [self._normalize_session_row(row)])
            )
            return

        self._submit(lambda: self._merge_session(row))

    def append_verification_session_event(self, event: VerificationSessionEvent) -> None:
        if not self._configured or self._client is None:
            return

        row = {
            "event_id": str(event.id),
            "session_id": str(event.session_id),
            "event_type": event.event_type.value,
            "occurred_at": _dt_to_iso(event.occurred_at),
            "received_at": _dt_to_iso(event.received_at),
            "metadata": event.metadata,
        }
        self._submit(
            lambda: self._insert_rows(self._events_table, [self._normalize_event_row(row)])
        )

    def _normalize_session_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "metadata": self._normalize_metadata(row.get("metadata"), self._sessions_metadata_type),
        }

    def _normalize_event_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "metadata": self._normalize_metadata(row.get("metadata"), self._events_metadata_type),
        }

    @staticmethod
    def _normalize_metadata(value: Any, field_type: str | None) -> Any:
        if field_type == "JSON":
            if isinstance(value, (dict, list)) or value is None:
                return value
            try:
                return json.loads(value)
            except Exception:
                return {"value": str(value)}
        # Default to STRING for portability
        try:
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        except Exception:
            return json.dumps({"value": str(value)}, ensure_ascii=False, separators=(",", ":"))

    def _submit(self, fn) -> None:
        if self._settings.bigquery_fail_requests:
            fn()
            return

        if self._executor is None:
            try:
                fn()
            except Exception as exc:
                logger.warning("BigQuery write failed (continuing): %s", exc)
            return

        future: Future[None] = self._executor.submit(_run_no_return, fn)
        future.add_done_callback(_log_future_exception)

    def _insert_rows(self, table_id: str, rows: list[dict[str, Any]]) -> None:
        assert self._client is not None
        errors = self._client.insert_rows_json(table_id, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert failed for {table_id}: {errors}")

    def _merge_session(self, row: dict[str, Any]) -> None:
        assert self._client is not None

        from google.cloud import bigquery  # type: ignore[import-not-found]

        # Use a portable metadata representation and adapt to JSON vs STRING column.
        metadata_json = self._normalize_metadata(row.get("metadata"), "STRING")
        metadata_expr = (
            "PARSE_JSON(@metadata_json)"
            if self._sessions_metadata_type == "JSON"
            else "@metadata_json"
        )

        # Upsert uses MERGE to avoid unbounded duplicates in `verification_sessions`.
        sql = f"""
        MERGE `{self._sessions_table}` T
        USING (
          SELECT
            @session_id AS session_id,
            @status AS status,
            @client_reference AS client_reference,
            {metadata_expr} AS metadata,
            @created_at AS created_at,
            @updated_at AS updated_at
        ) S
        ON T.session_id = S.session_id
        WHEN MATCHED THEN
          UPDATE SET
            status = S.status,
            client_reference = S.client_reference,
            metadata = S.metadata,
            updated_at = S.updated_at
        WHEN NOT MATCHED THEN
          INSERT (session_id, status, client_reference, metadata, created_at, updated_at)
          VALUES (
            S.session_id,
            S.status,
            S.client_reference,
            S.metadata,
            S.created_at,
            S.updated_at
          )
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("session_id", "STRING", row["session_id"]),
                bigquery.ScalarQueryParameter("status", "STRING", row["status"]),
                bigquery.ScalarQueryParameter(
                    "client_reference", "STRING", row.get("client_reference")
                ),
                bigquery.ScalarQueryParameter("metadata_json", "STRING", metadata_json),
                bigquery.ScalarQueryParameter(
                    "created_at", "TIMESTAMP", _iso_to_dt(row["created_at"])
                ),
                bigquery.ScalarQueryParameter(
                    "updated_at", "TIMESTAMP", _iso_to_dt(row["updated_at"])
                ),
            ]
        )
        self._client.query(sql, job_config=job_config).result()

    def _ensure_dataset(self) -> None:
        assert self._client is not None

        from google.cloud import bigquery  # type: ignore[import-not-found]

        dataset_id = f"{self._client.project}.{self._settings.bigquery_dataset}"
        try:
            self._client.get_dataset(dataset_id)
        except Exception:
            dataset = bigquery.Dataset(dataset_id)
            if self._settings.bigquery_location:
                dataset.location = self._settings.bigquery_location
            self._client.create_dataset(dataset, exists_ok=True)

    def _ensure_table(self, table_id: str, *, expectation: TableSchemaExpectation) -> None:
        assert self._client is not None

        from google.cloud import bigquery  # type: ignore[import-not-found]

        try:
            self._client.get_table(table_id)
            return
        except Exception:
            schema = _default_table_schema(bigquery, expectation)
            table = bigquery.Table(table_id, schema=schema)
            self._client.create_table(table, exists_ok=True)

    def _validate_table_schema(self, table_id: str, *, expectation: TableSchemaExpectation) -> None:
        assert self._client is not None
        table = self._client.get_table(table_id)
        problems = _schema_problems(table.schema, expectation)
        if problems:
            raise RuntimeError(f"{table_id} schema mismatch: " + "; ".join(problems))

    def _table_id(self, table: str) -> str:
        assert self._settings.bigquery_dataset
        project = self._settings.bigquery_project or (
            self._client.project if self._client else None
        )
        if not project:
            raise RuntimeError(
                "BIGQUERY_PROJECT must be set when BigQuery client has no default project"
            )
        return f"{project}.{self._settings.bigquery_dataset}.{table}"


def _schema_field_type(schema, field_name: str) -> str | None:
    for f in schema:
        if getattr(f, "name", None) == field_name:
            return getattr(f, "field_type", None)
    return None


def _schema_problems(schema, expectation: TableSchemaExpectation) -> list[str]:
    by_name: dict[str, str] = {f.name: f.field_type for f in schema}
    problems: list[str] = []
    for name, allowed_types in expectation.required_fields.items():
        actual = by_name.get(name)
        if actual is None:
            problems.append(f"missing column `{name}`")
            continue
        if actual.upper() not in {t.upper() for t in allowed_types}:
            problems.append(
                f"column `{name}` has type {actual}, expected one of {sorted(allowed_types)}"
            )
    return problems


def _default_table_schema(bigquery_module, expectation: TableSchemaExpectation):
    SchemaField = bigquery_module.SchemaField
    fields = []
    for name, allowed_types in expectation.required_fields.items():
        # Prefer stable, query-friendly types when auto-creating.
        if name == "metadata" and "JSON" in allowed_types:
            field_type = "JSON"
        elif name.endswith("_at") and "TIMESTAMP" in allowed_types:
            field_type = "TIMESTAMP"
        else:
            field_type = sorted(allowed_types)[0]
        fields.append(SchemaField(name=name, field_type=field_type, mode="NULLABLE"))
    return fields


def _iso_to_dt(value: str) -> datetime:
    # datetime.fromisoformat supports offsets like "+00:00"
    return datetime.fromisoformat(value)


def _run_no_return(fn) -> None:
    fn()


def _log_future_exception(future: Future[None]) -> None:
    exc = future.exception()
    if exc is not None:
        logger.warning("BigQuery async write failed (continuing): %s", exc)
