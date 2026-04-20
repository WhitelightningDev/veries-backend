from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VerificationSessionNotFoundError(Exception):
    session_id: UUID

    def __str__(self) -> str:  # pragma: no cover
        return f"Verification session not found: {self.session_id}"


@dataclass(frozen=True, slots=True)
class InvalidVerificationSessionStatusTransitionError(Exception):
    from_status: str
    to_status: str

    def __str__(self) -> str:  # pragma: no cover
        return f"Invalid status transition: {self.from_status} -> {self.to_status}"
