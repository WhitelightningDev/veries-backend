from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from veries_backend.app.api.schemas.verification_assets import VerificationAssetOut
from veries_backend.app.deps import get_uploads_service, get_verification_assets_service
from veries_backend.app.domain.verification_assets.types import VerificationAssetType
from veries_backend.app.services.uploads import UploadsService
from veries_backend.app.services.verification_assets import VerificationAssetsService

router = APIRouter(prefix="/verification-sessions")


@router.post(
    "/{session_id}/upload",
    response_model=VerificationAssetOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_verification_asset(
    session_id: UUID,
    customer_id: str = Form(...),
    asset_type: VerificationAssetType = Form(...),
    file: UploadFile = File(...),
    uploads: UploadsService = Depends(get_uploads_service),
    assets: VerificationAssetsService = Depends(get_verification_assets_service),
) -> VerificationAssetOut:
    result = uploads.upload(
        session_id=session_id,
        customer_id=customer_id,
        asset_type=asset_type,
        file=file,
    )
    asset = assets.get(result.asset_id)
    return VerificationAssetOut.from_domain(asset)
