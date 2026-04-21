from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"
    app_name: str = "veries-backend"
    api_prefix: str = "/api"

    # Analytics / BigQuery (optional)
    bigquery_enabled: bool = False
    bigquery_project: str | None = None
    bigquery_dataset: str | None = None
    bigquery_sessions_table: str = "verification_sessions"
    bigquery_events_table: str = "verification_session_events"
    bigquery_credentials_path: str | None = None
    bigquery_location: str | None = None
    bigquery_validate_on_startup: bool = True
    bigquery_autocreate_tables: bool = False
    bigquery_fail_requests: bool = False
    bigquery_async_writes: bool = True
    bigquery_async_max_workers: int = 2
    bigquery_session_write_mode: str = "merge"  # "merge" | "append"

    # Uploads (server-side)
    upload_storage_root: str = "var/uploads"
    max_image_upload_bytes: int = 10 * 1024 * 1024
    max_video_upload_bytes: int = 200 * 1024 * 1024

    # Cloud storage (optional)
    cloud_storage_enabled: bool = False
    gcs_project: str | None = None
    gcs_bucket: str | None = None
    gcs_video_bucket: str | None = None
    gcs_images_prefix: str = "images"
    gcs_videos_prefix: str = "videos"
    gcs_credentials_path: str | None = None

    @field_validator(
        "bigquery_project",
        "bigquery_dataset",
        "bigquery_credentials_path",
        "bigquery_location",
        "gcs_project",
        "gcs_bucket",
        "gcs_video_bucket",
        "gcs_credentials_path",
        mode="before",
    )
    @classmethod
    def _empty_string_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
