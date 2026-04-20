from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from veries_backend.app.api.schemas.verification_sessions import (
    VerificationSessionCreate,
    VerificationSessionOut,
    VerificationSessionUpdate,
)
from veries_backend.app.deps import get_verification_sessions_service
from veries_backend.app.services.verification_sessions import VerificationSessionsService

router = APIRouter(prefix="/verification-sessions")


@router.post("", response_model=VerificationSessionOut, status_code=status.HTTP_201_CREATED)
def create_verification_session(
    payload: VerificationSessionCreate,
    request: Request,
    response: Response,
    service: VerificationSessionsService = Depends(get_verification_sessions_service),
) -> VerificationSessionOut:
    session = service.create(client_reference=payload.client_reference, metadata=payload.metadata)
    response.headers["Location"] = str(
        request.url_for("get_verification_session", session_id=str(session.id))
    )
    return VerificationSessionOut.from_domain(session)


@router.get("/{session_id}", response_model=VerificationSessionOut)
def get_verification_session(
    session_id: UUID,
    service: VerificationSessionsService = Depends(get_verification_sessions_service),
) -> VerificationSessionOut:
    session = service.get(session_id)
    return VerificationSessionOut.from_domain(session)


@router.patch("/{session_id}", response_model=VerificationSessionOut)
def update_verification_session(
    session_id: UUID,
    payload: VerificationSessionUpdate,
    service: VerificationSessionsService = Depends(get_verification_sessions_service),
) -> VerificationSessionOut:
    session = service.update(session_id, status=payload.status, metadata=payload.metadata)
    return VerificationSessionOut.from_domain(session)
