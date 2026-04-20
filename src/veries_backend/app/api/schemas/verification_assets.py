from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from veries_backend.app.domain.verification_assets.model import VerificationAsset
from veries_backend.app.domain.verification_assets.status import VerificationAssetStatus
from veries_backend.app.domain.verification_assets.types import VerificationAssetType


class VerificationAssetCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=128)
    asset_type: VerificationAssetType
    mime_type: str = Field(min_length=1, max_length=128)
    storage_path: str | None = Field(default=None, max_length=512)


class VerificationAssetUpdate(BaseModel):
    status: VerificationAssetStatus | None = None
    storage_path: str | None = Field(default=None, max_length=512)
    mime_type: str | None = Field(default=None, max_length=128)
    uploaded_at: datetime | None = None


class VerificationAssetOut(BaseModel):
    id: UUID
    session_id: UUID
    customer_id: str
    asset_type: VerificationAssetType
    storage_path: str
    mime_type: str
    status: VerificationAssetStatus
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain(asset: VerificationAsset) -> VerificationAssetOut:
        return VerificationAssetOut(
            id=asset.id,
            session_id=asset.session_id,
            customer_id=asset.customer_id,
            asset_type=asset.asset_type,
            storage_path=asset.storage_path,
            mime_type=asset.mime_type,
            status=asset.status,
            uploaded_at=asset.uploaded_at,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )
