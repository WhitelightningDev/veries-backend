from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from veries_backend.app.api.schemas.verification_session_events import (
    VerificationSessionEventCreate,
    VerificationSessionEventOut,
)
from veries_backend.app.deps import get_verification_session_events_service
from veries_backend.app.services.verification_session_events import (
    VerificationSessionEventsService,
)

router = APIRouter(prefix="/verification-sessions")


@router.get(
    "/{session_id}/events",
    response_model=list[VerificationSessionEventOut],
)
def list_verification_session_events(
    session_id: UUID,
    service: VerificationSessionEventsService = Depends(get_verification_session_events_service),
) -> list[VerificationSessionEventOut]:
    events = service.list_for_session(session_id=session_id)
    return [VerificationSessionEventOut.from_domain(event) for event in events]


@router.post(
    "/{session_id}/events",
    response_model=VerificationSessionEventOut,
    status_code=status.HTTP_201_CREATED,
)
def log_verification_session_event(
    session_id: UUID,
    payload: VerificationSessionEventCreate,
    service: VerificationSessionEventsService = Depends(get_verification_session_events_service),
) -> VerificationSessionEventOut:
    event = service.log_event(
        session_id=session_id,
        event_type=payload.event_type,
        occurred_at=payload.occurred_at,
        metadata=payload.metadata,
    )
    return VerificationSessionEventOut.from_domain(event)
