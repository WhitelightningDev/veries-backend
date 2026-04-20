from __future__ import annotations

from typing import Protocol
from uuid import UUID

from veries_backend.app.domain.verification_sessions.model import VerificationSession


class VerificationSessionsRepo(Protocol):
    def create(self, session: VerificationSession) -> VerificationSession: ...

    def get(self, session_id: UUID) -> VerificationSession | None: ...

    def update(self, session: VerificationSession) -> VerificationSession: ...
