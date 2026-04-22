from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from veries_backend.app.analytics.sink import AnalyticsSink
from veries_backend.app.domain.verification_sessions.events import (
    VerificationSessionEvent,
    VerificationSessionEventType,
)
from veries_backend.app.domain.verification_sessions.events_repo import (
    VerificationSessionEventsRepo,
)
from veries_backend.app.services.verification_sessions import VerificationSessionsService


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VerificationSessionEventsService:
    def __init__(
        self,
        *,
        sessions: VerificationSessionsService,
        repo: VerificationSessionEventsRepo,
        analytics: AnalyticsSink,
    ) -> None:
        self._sessions = sessions
        self._repo = repo
        self._analytics = analytics

    def log_event(
        self,
        *,
        session_id: UUID,
        event_type: VerificationSessionEventType,
        occurred_at: datetime | None,
        metadata: dict[str, Any],
    ) -> VerificationSessionEvent:
        self._sessions.get(session_id)
        event = VerificationSessionEvent(
            session_id=session_id,
            event_type=event_type,
            occurred_at=occurred_at or _utc_now(),
            received_at=_utc_now(),
            metadata=metadata,
        )
        event = self._repo.create(event)
        self._analytics.append_verification_session_event(event)
        return event

    def list_for_session(self, *, session_id: UUID) -> list[VerificationSessionEvent]:
        self._sessions.get(session_id)
        return self._repo.list_for_session(session_id)
