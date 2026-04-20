from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status

from veries_backend.app.domain.verification_assets.model import VerificationAsset
from veries_backend.app.domain.verification_assets.repo import VerificationAssetsRepo
from veries_backend.app.domain.verification_assets.status import VerificationAssetStatus
from veries_backend.app.domain.verification_assets.types import VerificationAssetType
from veries_backend.app.services.verification_sessions import VerificationSessionsService

_SEGMENT_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sanitize_segment(value: str) -> str:
    value = value.strip()
    value = value.replace("/", "_")
    value = _SEGMENT_RE.sub("_", value)
    return value.strip("_") or "unknown"


def _guess_extension(mime_type: str) -> str:
    mime_type = (mime_type or "").lower().strip()
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/heic": ".heic",
        "image/heif": ".heif",
        "application/pdf": ".pdf",
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
    }.get(mime_type, "")


def build_storage_path(
    *,
    customer_id: str,
    session_id: UUID,
    asset_type: VerificationAssetType,
    asset_id: UUID,
    mime_type: str,
) -> str:
    customer = _sanitize_segment(customer_id)
    ext = _guess_extension(mime_type)
    return (
        f"verifications/{customer}/verification-sessions/{session_id}/{asset_type.value}/{asset_id}"
        f"{ext}"
    )


class VerificationAssetsService:
    def __init__(
        self,
        *,
        sessions: VerificationSessionsService,
        repo: VerificationAssetsRepo,
    ) -> None:
        self._sessions = sessions
        self._repo = repo

    def create(
        self,
        *,
        session_id: UUID,
        customer_id: str,
        asset_type: VerificationAssetType,
        mime_type: str,
        storage_path: str | None,
    ) -> VerificationAsset:
        self._sessions.get(session_id)

        asset = VerificationAsset(
            session_id=session_id,
            customer_id=customer_id,
            asset_type=asset_type,
            mime_type=mime_type,
            status=VerificationAssetStatus.PENDING,
            storage_path="",
        )
        asset.storage_path = storage_path or build_storage_path(
            customer_id=customer_id,
            session_id=session_id,
            asset_type=asset_type,
            asset_id=asset.id,
            mime_type=mime_type,
        )
        return self._repo.create(asset)

    def get(self, asset_id: UUID) -> VerificationAsset:
        asset = self._repo.get(asset_id)
        if asset is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail="Asset not found"
            )
        return asset

    def list_for_session(self, session_id: UUID) -> list[VerificationAsset]:
        self._sessions.get(session_id)
        return self._repo.list_for_session(session_id)

    def update(
        self,
        asset_id: UUID,
        *,
        status: VerificationAssetStatus | None,
        storage_path: str | None,
        mime_type: str | None,
        uploaded_at: datetime | None,
    ) -> VerificationAsset:
        asset = self.get(asset_id)

        if uploaded_at is not None and status != VerificationAssetStatus.UPLOADED:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="uploaded_at can only be set when status is uploaded",
            )

        touched = False
        if mime_type is not None:
            asset.mime_type = mime_type
            touched = True

        if storage_path is not None:
            asset.storage_path = storage_path
            touched = True

        if status is not None:
            if status == VerificationAssetStatus.UPLOADED:
                asset.mark_uploaded(uploaded_at=uploaded_at)
            else:
                asset.mark_status(status)
            touched = True

        if touched and status is None:
            asset.updated_at = _utc_now()

        return self._repo.update(asset)
