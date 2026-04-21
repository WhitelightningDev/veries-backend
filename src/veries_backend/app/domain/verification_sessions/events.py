from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class VerificationSessionEventType(str, Enum):
    SESSION_STARTED = "session_started"
    CAMERA_OPENED = "camera_opened"
    CAMERA_PERMISSION_GRANTED = "camera_permission_granted"
    CAMERA_PERMISSION_DENIED = "camera_permission_denied"
    MODE_SWITCHED = "mode_switched"
    CAPTURE_TAKEN = "capture_taken"
    CAPTURE_RETAKEN = "capture_retaken"
    DROP_OFF = "drop_off"
    RESUME = "resume"
    SUBMISSION_CONFIRMED = "submission_confirmed"
    COMPLETED = "completed"
    UPLOAD_STARTED = "upload_started"
    UPLOAD_COMPLETED = "upload_completed"
    UPLOAD_FAILED = "upload_failed"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class VerificationSessionEvent:
    id: UUID = field(default_factory=uuid4)
    session_id: UUID = field(default_factory=uuid4)
    event_type: VerificationSessionEventType = VerificationSessionEventType.SESSION_STARTED
    occurred_at: datetime = field(default_factory=_utc_now)
    received_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
