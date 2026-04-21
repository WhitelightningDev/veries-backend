from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import Depends

from veries_backend.app.analytics.noop import NoOpAnalyticsSink
from veries_backend.app.analytics.sink import AnalyticsSink
from veries_backend.app.core.config import get_settings
from veries_backend.app.domain.verification_assets.repo import VerificationAssetsRepo
from veries_backend.app.domain.verification_sessions.events_repo import (
    VerificationSessionEventsRepo,
)
from veries_backend.app.domain.verification_sessions.repo import VerificationSessionsRepo
from veries_backend.app.infra.verification_assets_in_memory import (
    in_memory_verification_assets_repo,
)
from veries_backend.app.infra.verification_session_events_in_memory import (
    in_memory_verification_session_events_repo,
)
from veries_backend.app.infra.verification_sessions_in_memory import (
    in_memory_verification_sessions_repo,
)
from veries_backend.app.services.uploads import UploadsService
from veries_backend.app.services.verification_assets import VerificationAssetsService
from veries_backend.app.services.verification_session_events import (
    VerificationSessionEventsService,
)
from veries_backend.app.services.verification_sessions import VerificationSessionsService
from veries_backend.app.storage.base import ObjectStorage
from veries_backend.app.storage.gcs import GCSObjectStorage
from veries_backend.app.storage.local import LocalObjectStorage


@lru_cache(maxsize=1)
def get_analytics_sink() -> AnalyticsSink:
    settings = get_settings()
    if not settings.bigquery_enabled:
        return NoOpAnalyticsSink()

    try:
        from veries_backend.app.analytics.bigquery_sink import BigQueryAnalyticsSink
    except ImportError as exc:
        # Keep the verification flow working even if optional deps aren't installed.
        logging.getLogger("veries_backend.analytics.bigquery").warning(
            "BigQuery disabled (dependency missing): %s", exc
        )
        return NoOpAnalyticsSink()

    sink = BigQueryAnalyticsSink(settings=settings)
    return sink


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    if not settings.cloud_storage_enabled:
        return LocalObjectStorage(root=settings.upload_storage_root)

    return GCSObjectStorage(
        project=settings.gcs_project, credentials_path=settings.gcs_credentials_path
    )


def get_verification_sessions_repo() -> VerificationSessionsRepo:
    return in_memory_verification_sessions_repo


def get_verification_session_events_repo() -> VerificationSessionEventsRepo:
    return in_memory_verification_session_events_repo


def get_verification_assets_repo() -> VerificationAssetsRepo:
    return in_memory_verification_assets_repo


def get_verification_sessions_service(
    repo: VerificationSessionsRepo = Depends(get_verification_sessions_repo),
    events_repo: VerificationSessionEventsRepo = Depends(get_verification_session_events_repo),
    analytics: AnalyticsSink = Depends(get_analytics_sink),
) -> VerificationSessionsService:
    return VerificationSessionsService(repo=repo, analytics=analytics, events_repo=events_repo)


def get_verification_session_events_service(
    sessions: VerificationSessionsService = Depends(get_verification_sessions_service),
    repo: VerificationSessionEventsRepo = Depends(get_verification_session_events_repo),
    analytics: AnalyticsSink = Depends(get_analytics_sink),
) -> VerificationSessionEventsService:
    return VerificationSessionEventsService(sessions=sessions, repo=repo, analytics=analytics)


def get_verification_assets_service(
    sessions: VerificationSessionsService = Depends(get_verification_sessions_service),
    repo: VerificationAssetsRepo = Depends(get_verification_assets_repo),
) -> VerificationAssetsService:
    return VerificationAssetsService(sessions=sessions, repo=repo)


def get_uploads_service(
    sessions: VerificationSessionsService = Depends(get_verification_sessions_service),
    assets: VerificationAssetsService = Depends(get_verification_assets_service),
    events: VerificationSessionEventsService = Depends(get_verification_session_events_service),
) -> UploadsService:
    settings = get_settings()
    storage = get_object_storage()

    if settings.cloud_storage_enabled:
        images_bucket = settings.gcs_bucket or ""
        videos_bucket = settings.gcs_video_bucket or settings.gcs_bucket or ""
        images_prefix = settings.gcs_images_prefix
        videos_prefix = settings.gcs_videos_prefix
    else:
        images_bucket = ""
        videos_bucket = ""
        images_prefix = ""
        videos_prefix = ""

    return UploadsService(
        sessions=sessions,
        assets=assets,
        events=events,
        storage=storage,
        images_bucket=images_bucket,
        videos_bucket=videos_bucket,
        images_prefix=images_prefix,
        videos_prefix=videos_prefix,
        max_image_upload_bytes=settings.max_image_upload_bytes,
        max_video_upload_bytes=settings.max_video_upload_bytes,
    )
