from __future__ import annotations

from enum import Enum


class VerificationAssetStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"
