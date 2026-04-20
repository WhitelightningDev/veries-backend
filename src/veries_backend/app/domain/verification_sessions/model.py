from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from veries_backend.app.domain.verification_sessions.status import VerificationSessionStatus


@dataclass(frozen=True, slots=True)
class StatusEvent:
    status: VerificationSessionStatus
    at: datetime


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class VerificationSession:
    id: UUID = field(default_factory=uuid4)
    status: VerificationSessionStatus = VerificationSessionStatus.STARTED
    client_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    status_history: list[StatusEvent] = field(default_factory=list)

    @staticmethod
    def new(*, client_reference: str | None, metadata: dict[str, Any]) -> VerificationSession:
        now = _utc_now()
        session = VerificationSession(
            status=VerificationSessionStatus.STARTED,
            client_reference=client_reference,
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )
        session.status_history.append(StatusEvent(status=session.status, at=now))
        return session

    def set_status(self, status: VerificationSessionStatus) -> None:
        if status == self.status:
            return
        now = _utc_now()
        self.status = status
        self.updated_at = now
        self.status_history.append(StatusEvent(status=status, at=now))

    def set_metadata(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata
        self.updated_at = _utc_now()
