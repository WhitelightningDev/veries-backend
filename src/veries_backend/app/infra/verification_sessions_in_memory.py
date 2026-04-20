from __future__ import annotations

from threading import Lock
from uuid import UUID

from veries_backend.app.domain.verification_sessions.model import VerificationSession
from veries_backend.app.domain.verification_sessions.repo import VerificationSessionsRepo


class InMemoryVerificationSessionsRepo(VerificationSessionsRepo):
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[UUID, VerificationSession] = {}

    def create(self, session: VerificationSession) -> VerificationSession:
        with self._lock:
            self._sessions[session.id] = session
            return session

    def get(self, session_id: UUID) -> VerificationSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def update(self, session: VerificationSession) -> VerificationSession:
        with self._lock:
            self._sessions[session.id] = session
            return session


in_memory_verification_sessions_repo = InMemoryVerificationSessionsRepo()
