from __future__ import annotations

from typing import Protocol
from uuid import UUID

from veries_backend.app.domain.verification_sessions.events import VerificationSessionEvent


class VerificationSessionEventsRepo(Protocol):
    def create(self, event: VerificationSessionEvent) -> VerificationSessionEvent: ...

    def list_for_session(self, session_id: UUID) -> list[VerificationSessionEvent]: ...
