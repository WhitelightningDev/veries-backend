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

    # CORS (browser frontend)
    # Accepts: empty, "*" or comma-separated origins in `CORS_ORIGINS`.
    cors_origins: list[str] = []
    cors_allow_credentials: bool = False

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

    # Vision (OpenCV) - optional upload hardening
    vision_enabled: bool = True
    vision_require_decodable_images: bool = True
    vision_enforce_quality: bool = True
    vision_min_image_side_px: int = 600
    vision_max_glare_ratio: float = 0.12
    vision_min_blur_variance: float = 60.0
    vision_min_brightness: float = 40.0
    vision_max_brightness: float = 220.0
    vision_max_faces: int = 1
    vision_min_face_area_ratio: float = 0.02
    vision_min_document_area_ratio: float = 0.25

    # Cloud storage (optional)
    cloud_storage_enabled: bool = False
    gcs_project: str | None = None
    gcs_bucket: str | None = None
    gcs_video_bucket: str | None = None
    gcs_images_prefix: str = "images"
    gcs_videos_prefix: str = "videos"
    gcs_credentials_path: str | None = None

    @field_validator(
        "cors_origins",
        mode="before",
    )
    @classmethod
    def _parse_cors_origins(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s == "*":
                return ["*"]
            return [part.strip() for part in s.split(",") if part.strip()]
        if isinstance(v, (list, tuple)):
            return [str(part).strip() for part in v if str(part).strip()]
        return v

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
