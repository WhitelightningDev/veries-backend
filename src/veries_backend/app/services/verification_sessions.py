from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status

from veries_backend.app.analytics.sink import AnalyticsSink
from veries_backend.app.domain.verification_sessions.errors import (
    InvalidVerificationSessionStatusTransitionError,
    VerificationSessionNotFoundError,
)
from veries_backend.app.domain.verification_sessions.model import VerificationSession
from veries_backend.app.domain.verification_sessions.repo import VerificationSessionsRepo
from veries_backend.app.domain.verification_sessions.status import VerificationSessionStatus

_ALLOWED_TRANSITIONS: dict[VerificationSessionStatus, set[VerificationSessionStatus]] = {
    VerificationSessionStatus.STARTED: {
        VerificationSessionStatus.IN_PROGRESS,
        VerificationSessionStatus.DROPPED_OFF,
        VerificationSessionStatus.FAILED,
    },
    VerificationSessionStatus.IN_PROGRESS: {
        VerificationSessionStatus.DROPPED_OFF,
        VerificationSessionStatus.SUBMITTED,
        VerificationSessionStatus.COMPLETED,
        VerificationSessionStatus.FAILED,
    },
    VerificationSessionStatus.DROPPED_OFF: {
        VerificationSessionStatus.RESUMED,
        VerificationSessionStatus.FAILED,
    },
    VerificationSessionStatus.RESUMED: {
        VerificationSessionStatus.IN_PROGRESS,
        VerificationSessionStatus.DROPPED_OFF,
        VerificationSessionStatus.SUBMITTED,
        VerificationSessionStatus.FAILED,
    },
    VerificationSessionStatus.SUBMITTED: {
        VerificationSessionStatus.COMPLETED,
        VerificationSessionStatus.FAILED,
    },
    VerificationSessionStatus.COMPLETED: set(),
    VerificationSessionStatus.FAILED: set(),
}


def _validate_transition(
    from_status: VerificationSessionStatus, to_status: VerificationSessionStatus
) -> None:
    if to_status == from_status:
        return
    allowed = _ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidVerificationSessionStatusTransitionError(
            from_status=from_status.value, to_status=to_status.value
        )


class VerificationSessionsService:
    def __init__(self, *, repo: VerificationSessionsRepo, analytics: AnalyticsSink) -> None:
        self._repo = repo
        self._analytics = analytics

    def create(
        self, *, client_reference: str | None, metadata: dict[str, Any]
    ) -> VerificationSession:
        session = VerificationSession.new(client_reference=client_reference, metadata=metadata)
        session = self._repo.create(session)
        self._analytics.upsert_verification_session(session)
        return session

    def get(self, session_id: UUID) -> VerificationSession:
        session = self._repo.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail="Session not found"
            )
        return session

    def update(
        self,
        session_id: UUID,
        *,
        status: VerificationSessionStatus | None,
        metadata: dict[str, Any] | None,
    ) -> VerificationSession:
        session = self._repo.get(session_id)
        if session is None:
            self._raise_not_found(VerificationSessionNotFoundError(session_id=session_id))

        if status is not None:
            try:
                _validate_transition(session.status, status)
            except InvalidVerificationSessionStatusTransitionError as exc:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail=str(exc),
                ) from exc
            session.set_status(status)

        if metadata is not None:
            session.set_metadata(metadata)

        session = self._repo.update(session)
        self._analytics.upsert_verification_session(session)
        return session

    @staticmethod
    def _raise_not_found(exc: VerificationSessionNotFoundError) -> None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
