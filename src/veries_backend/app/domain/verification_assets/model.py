from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from veries_backend.app.domain.verification_assets.status import VerificationAssetStatus
from veries_backend.app.domain.verification_assets.types import VerificationAssetType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class VerificationAsset:
    id: UUID = field(default_factory=uuid4)
    session_id: UUID = field(default_factory=uuid4)
    customer_id: str = ""
    asset_type: VerificationAssetType = VerificationAssetType.ID_DOCUMENT
    storage_path: str = ""
    mime_type: str = ""
    status: VerificationAssetStatus = VerificationAssetStatus.PENDING
    uploaded_at: datetime | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def mark_status(self, status: VerificationAssetStatus) -> None:
        if status == self.status:
            return
        self.status = status
        self.updated_at = _utc_now()

    def mark_uploaded(self, *, uploaded_at: datetime | None = None) -> None:
        self.status = VerificationAssetStatus.UPLOADED
        self.uploaded_at = uploaded_at or _utc_now()
        self.updated_at = _utc_now()
