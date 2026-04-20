from __future__ import annotations

from enum import Enum


class VerificationSessionStatus(str, Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    DROPPED_OFF = "dropped_off"
    RESUMED = "resumed"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"
