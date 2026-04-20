from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from veries_backend.app.domain.verification_sessions.model import VerificationSession
from veries_backend.app.domain.verification_sessions.status import VerificationSessionStatus


class VerificationSessionCreate(BaseModel):
    client_reference: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationSessionUpdate(BaseModel):
    status: VerificationSessionStatus | None = None
    metadata: dict[str, Any] | None = None


class StatusEventOut(BaseModel):
    status: VerificationSessionStatus
    at: datetime


class VerificationSessionOut(BaseModel):
    id: UUID
    status: VerificationSessionStatus
    client_reference: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    status_history: list[StatusEventOut]

    @staticmethod
    def from_domain(session: VerificationSession) -> VerificationSessionOut:
        return VerificationSessionOut(
            id=session.id,
            status=session.status,
            client_reference=session.client_reference,
            metadata=session.metadata,
            created_at=session.created_at,
            updated_at=session.updated_at,
            status_history=[
                StatusEventOut(status=event.status, at=event.at) for event in session.status_history
            ],
        )
