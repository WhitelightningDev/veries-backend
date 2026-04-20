from __future__ import annotations

from typing import Protocol

from veries_backend.app.domain.verification_sessions.events import VerificationSessionEvent
from veries_backend.app.domain.verification_sessions.model import VerificationSession


class AnalyticsSink(Protocol):
    def upsert_verification_session(self, session: VerificationSession) -> None: ...

    def append_verification_session_event(self, event: VerificationSessionEvent) -> None: ...
