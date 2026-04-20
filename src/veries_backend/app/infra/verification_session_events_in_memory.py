from __future__ import annotations

from threading import Lock
from uuid import UUID

from veries_backend.app.domain.verification_sessions.events import VerificationSessionEvent
from veries_backend.app.domain.verification_sessions.events_repo import (
    VerificationSessionEventsRepo,
)


class InMemoryVerificationSessionEventsRepo(VerificationSessionEventsRepo):
    def __init__(self) -> None:
        self._lock = Lock()
        self._events_by_session: dict[UUID, list[VerificationSessionEvent]] = {}

    def create(self, event: VerificationSessionEvent) -> VerificationSessionEvent:
        with self._lock:
            self._events_by_session.setdefault(event.session_id, []).append(event)
            return event

    def list_for_session(self, session_id: UUID) -> list[VerificationSessionEvent]:
        with self._lock:
            return list(self._events_by_session.get(session_id, []))


in_memory_verification_session_events_repo = InMemoryVerificationSessionEventsRepo()
