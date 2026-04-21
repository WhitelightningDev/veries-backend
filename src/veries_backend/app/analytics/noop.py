from __future__ import annotations

from veries_backend.app.analytics.sink import AnalyticsSink
from veries_backend.app.domain.verification_sessions.events import VerificationSessionEvent
from veries_backend.app.domain.verification_sessions.model import VerificationSession


class NoOpAnalyticsSink(AnalyticsSink):
    def upsert_verification_session(self, session: VerificationSession) -> None:
        return

    def append_verification_session_event(self, event: VerificationSessionEvent) -> None:
        return

    def close(self) -> None:
        return
