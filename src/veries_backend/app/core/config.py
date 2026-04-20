from __future__ import annotations

from functools import lru_cache

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
