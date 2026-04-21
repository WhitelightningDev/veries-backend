from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status

from veries_backend.app.analytics.sink import AnalyticsSink
from veries_backend.app.domain.verification_sessions.errors import (
    InvalidVerificationSessionStatusTransitionError,
    VerificationSessionNotFoundError,
)
from veries_backend.app.domain.verification_sessions.events import (
    VerificationSessionEvent,
    VerificationSessionEventType,
)
from veries_backend.app.domain.verification_sessions.events_repo import (
    VerificationSessionEventsRepo,
)
from veries_backend.app.domain.verification_sessions.model import VerificationSession
from veries_backend.app.domain.verification_sessions.repo import VerificationSessionsRepo
from veries_backend.app.domain.verification_sessions.status import VerificationSessionStatus

logger = logging.getLogger("veries_backend.sessions")

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
    def __init__(
        self,
        *,
        repo: VerificationSessionsRepo,
        analytics: AnalyticsSink,
        events_repo: VerificationSessionEventsRepo | None = None,
    ) -> None:
        self._repo = repo
        self._analytics = analytics
        self._events_repo = events_repo

    def create(
        self, *, client_reference: str | None, metadata: dict[str, Any]
    ) -> VerificationSession:
        session = VerificationSession.new(client_reference=client_reference, metadata=metadata)
        session = self._repo.create(session)
        self._analytics.upsert_verification_session(session)
        self._emit_lifecycle_event_if_needed(
            session=session,
            event_type=VerificationSessionEventType.SESSION_STARTED,
            occurred_at=session.created_at,
            from_status=None,
        )
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

        previous_status = session.status
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

        if status is not None and status != previous_status:
            mapping: dict[VerificationSessionStatus, VerificationSessionEventType] = {
                VerificationSessionStatus.STARTED: VerificationSessionEventType.SESSION_STARTED,
                VerificationSessionStatus.DROPPED_OFF: VerificationSessionEventType.DROP_OFF,
                VerificationSessionStatus.RESUMED: VerificationSessionEventType.RESUME,
                VerificationSessionStatus.SUBMITTED: (
                    VerificationSessionEventType.SUBMISSION_CONFIRMED
                ),
                VerificationSessionStatus.COMPLETED: VerificationSessionEventType.COMPLETED,
            }
            event_type = mapping.get(status)
            if event_type is not None:
                occurred_at = (
                    session.status_history[-1].at if session.status_history else session.updated_at
                )
                self._emit_lifecycle_event_if_needed(
                    session=session,
                    event_type=event_type,
                    occurred_at=occurred_at,
                    from_status=previous_status,
                )

        return session

    @staticmethod
    def _raise_not_found(exc: VerificationSessionNotFoundError) -> None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    def _emit_lifecycle_event_if_needed(
        self,
        *,
        session: VerificationSession,
        event_type: VerificationSessionEventType,
        occurred_at: datetime,
        from_status: VerificationSessionStatus | None,
    ) -> None:
        if self._events_repo is None:
            return

        try:
            existing = self._events_repo.list_for_session(session.id)
            for ev in reversed(existing):
                if ev.event_type != event_type:
                    continue
                # Dedupe: if a matching event already exists near this transition timestamp, skip.
                delta = abs((ev.occurred_at - occurred_at).total_seconds())
                if delta <= 10:
                    return

            event = VerificationSessionEvent(
                session_id=session.id,
                event_type=event_type,
                occurred_at=occurred_at,
                metadata={
                    "source": "system",
                    "status": session.status.value,
                    "from_status": from_status.value if from_status else None,
                },
            )
            self._events_repo.create(event)
            self._analytics.append_verification_session_event(event)
        except Exception as exc:
            logger.warning("lifecycle event emission failed (continuing): %s", exc)
