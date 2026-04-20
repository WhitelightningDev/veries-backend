from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from veries_backend.app.api.schemas.verification_assets import (
    VerificationAssetCreate,
    VerificationAssetOut,
    VerificationAssetUpdate,
)
from veries_backend.app.deps import get_verification_assets_service
from veries_backend.app.services.verification_assets import VerificationAssetsService

router = APIRouter()


@router.post(
    "/verification-sessions/{session_id}/assets",
    response_model=VerificationAssetOut,
    status_code=status.HTTP_201_CREATED,
)
def create_verification_asset(
    session_id: UUID,
    payload: VerificationAssetCreate,
    service: VerificationAssetsService = Depends(get_verification_assets_service),
) -> VerificationAssetOut:
    asset = service.create(
        session_id=session_id,
        customer_id=payload.customer_id,
        asset_type=payload.asset_type,
        mime_type=payload.mime_type,
        storage_path=payload.storage_path,
    )
    return VerificationAssetOut.from_domain(asset)


@router.get(
    "/verification-sessions/{session_id}/assets",
    response_model=list[VerificationAssetOut],
)
def list_verification_assets(
    session_id: UUID,
    service: VerificationAssetsService = Depends(get_verification_assets_service),
) -> list[VerificationAssetOut]:
    assets = service.list_for_session(session_id)
    return [VerificationAssetOut.from_domain(asset) for asset in assets]


@router.patch("/verification-assets/{asset_id}", response_model=VerificationAssetOut)
def update_verification_asset(
    asset_id: UUID,
    payload: VerificationAssetUpdate,
    service: VerificationAssetsService = Depends(get_verification_assets_service),
) -> VerificationAssetOut:
    asset = service.update(
        asset_id,
        status=payload.status,
        storage_path=payload.storage_path,
        mime_type=payload.mime_type,
        uploaded_at=payload.uploaded_at,
    )
    return VerificationAssetOut.from_domain(asset)
