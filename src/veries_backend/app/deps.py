from __future__ import annotations

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
from veries_backend.app.services.verification_assets import VerificationAssetsService
from veries_backend.app.services.verification_session_events import (
    VerificationSessionEventsService,
)
from veries_backend.app.services.verification_sessions import VerificationSessionsService


@lru_cache(maxsize=1)
def get_analytics_sink() -> AnalyticsSink:
    settings = get_settings()
    if not settings.bigquery_enabled:
        return NoOpAnalyticsSink()

    from veries_backend.app.analytics.bigquery_sink import BigQueryAnalyticsSink

    return BigQueryAnalyticsSink(settings=settings)


def get_verification_sessions_repo() -> VerificationSessionsRepo:
    return in_memory_verification_sessions_repo


def get_verification_session_events_repo() -> VerificationSessionEventsRepo:
    return in_memory_verification_session_events_repo


def get_verification_assets_repo() -> VerificationAssetsRepo:
    return in_memory_verification_assets_repo


def get_verification_sessions_service(
    repo: VerificationSessionsRepo = Depends(get_verification_sessions_repo),
    analytics: AnalyticsSink = Depends(get_analytics_sink),
) -> VerificationSessionsService:
    return VerificationSessionsService(repo=repo, analytics=analytics)


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
