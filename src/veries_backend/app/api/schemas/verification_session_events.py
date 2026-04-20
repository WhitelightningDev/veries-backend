from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from veries_backend.app.domain.verification_sessions.events import (
    VerificationSessionEvent,
    VerificationSessionEventType,
)


class VerificationSessionEventCreate(BaseModel):
    event_type: VerificationSessionEventType
    occurred_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationSessionEventOut(BaseModel):
    id: UUID
    session_id: UUID
    event_type: VerificationSessionEventType
    occurred_at: datetime
    received_at: datetime
    metadata: dict[str, Any]

    @staticmethod
    def from_domain(event: VerificationSessionEvent) -> VerificationSessionEventOut:
        return VerificationSessionEventOut(
            id=event.id,
            session_id=event.session_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            received_at=event.received_at,
            metadata=event.metadata,
        )
