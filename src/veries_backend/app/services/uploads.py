from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from uuid import UUID

from fastapi import HTTPException, UploadFile
from fastapi import status as http_status

from veries_backend.app.domain.verification_assets.status import VerificationAssetStatus
from veries_backend.app.domain.verification_assets.types import VerificationAssetType
from veries_backend.app.domain.verification_sessions.events import VerificationSessionEventType
from veries_backend.app.services.verification_assets import VerificationAssetsService
from veries_backend.app.services.verification_session_events import VerificationSessionEventsService
from veries_backend.app.services.verification_sessions import VerificationSessionsService

_CHUNK_SIZE: Final[int] = 1024 * 1024

_IMAGE_MIME_TYPES: Final[set[str]] = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/heic",
    "image/heif",
}

_ID_DOC_EXTRA_MIME_TYPES: Final[set[str]] = {
    "application/pdf",
}

_VIDEO_MIME_TYPES: Final[set[str]] = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
}


@dataclass(frozen=True, slots=True)
class UploadResult:
    asset_id: UUID
    storage_path: str
    bytes_written: int


class UploadsService:
    def __init__(
        self,
        *,
        sessions: VerificationSessionsService,
        assets: VerificationAssetsService,
        events: VerificationSessionEventsService,
        storage_root: str,
        max_image_upload_bytes: int,
        max_video_upload_bytes: int,
    ) -> None:
        self._sessions = sessions
        self._assets = assets
        self._events = events
        self._storage_root = Path(storage_root)
        self._max_image_upload_bytes = max_image_upload_bytes
        self._max_video_upload_bytes = max_video_upload_bytes

    def upload(
        self,
        *,
        session_id: UUID,
        customer_id: str,
        asset_type: VerificationAssetType,
        file: UploadFile,
    ) -> UploadResult:
        self._sessions.get(session_id)

        mime_type = (file.content_type or "").lower().strip()
        self._validate_mime(asset_type, mime_type)

        asset = self._assets.create(
            session_id=session_id,
            customer_id=customer_id,
            asset_type=asset_type,
            mime_type=mime_type,
            storage_path=None,
        )
        self._assets.update(
            asset.id,
            status=VerificationAssetStatus.UPLOADING,
            storage_path=None,
            mime_type=None,
            uploaded_at=None,
        )

        self._events.log_event(
            session_id=session_id,
            event_type=VerificationSessionEventType.UPLOAD_STARTED,
            occurred_at=None,
            metadata={
                "asset_id": str(asset.id),
                "asset_type": asset_type.value,
                "filename": file.filename,
                "mime_type": mime_type,
            },
        )

        dest = self._safe_dest_path(asset.storage_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        bytes_written = 0
        try:
            bytes_written = self._write_stream(
                file=file,
                dest=dest,
                max_bytes=self._max_bytes_for(asset_type),
            )
            self._assets.update(
                asset.id,
                status=VerificationAssetStatus.UPLOADED,
                storage_path=None,
                mime_type=None,
                uploaded_at=None,
            )
            self._events.log_event(
                session_id=session_id,
                event_type=VerificationSessionEventType.UPLOAD_COMPLETED,
                occurred_at=None,
                metadata={
                    "asset_id": str(asset.id),
                    "asset_type": asset_type.value,
                    "bytes": bytes_written,
                    "storage_path": asset.storage_path,
                    "mime_type": mime_type,
                },
            )
            return UploadResult(
                asset_id=asset.id,
                storage_path=asset.storage_path,
                bytes_written=bytes_written,
            )
        except HTTPException as exc:
            self._assets.update(
                asset.id,
                status=VerificationAssetStatus.FAILED,
                storage_path=None,
                mime_type=None,
                uploaded_at=None,
            )
            self._events.log_event(
                session_id=session_id,
                event_type=VerificationSessionEventType.UPLOAD_FAILED,
                occurred_at=None,
                metadata={
                    "asset_id": str(asset.id),
                    "asset_type": asset_type.value,
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                },
            )
            raise
        except Exception as exc:  # pragma: no cover
            self._assets.update(
                asset.id,
                status=VerificationAssetStatus.FAILED,
                storage_path=None,
                mime_type=None,
                uploaded_at=None,
            )
            self._events.log_event(
                session_id=session_id,
                event_type=VerificationSessionEventType.UPLOAD_FAILED,
                occurred_at=None,
                metadata={
                    "asset_id": str(asset.id),
                    "asset_type": asset_type.value,
                    "detail": str(exc),
                },
            )
            raise

    def _max_bytes_for(self, asset_type: VerificationAssetType) -> int:
        if asset_type == VerificationAssetType.BACKGROUND_VIDEO:
            return self._max_video_upload_bytes
        return self._max_image_upload_bytes

    @staticmethod
    def _validate_mime(asset_type: VerificationAssetType, mime_type: str) -> None:
        if not mime_type:
            raise HTTPException(
                status_code=http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Missing content-type",
            )

        if asset_type == VerificationAssetType.BACKGROUND_VIDEO:
            if mime_type not in _VIDEO_MIME_TYPES:
                raise HTTPException(
                    status_code=http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Invalid video content-type",
                )
            return

        allowed = set(_IMAGE_MIME_TYPES)
        if asset_type == VerificationAssetType.ID_DOCUMENT:
            allowed |= _ID_DOC_EXTRA_MIME_TYPES

        if mime_type not in allowed:
            raise HTTPException(
                status_code=http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Invalid image/document content-type",
            )

    def _safe_dest_path(self, storage_path: str) -> Path:
        root = self._storage_root.resolve()
        dest = (root / storage_path).resolve()
        if os.path.commonpath([str(root), str(dest)]) != str(root):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage path",
            )
        return dest

    @staticmethod
    def _write_stream(*, file: UploadFile, dest: Path, max_bytes: int) -> int:
        bytes_written = 0
        try:
            with dest.open("wb") as f:
                while True:
                    chunk = file.file.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise HTTPException(
                            status_code=http_status.HTTP_413_CONTENT_TOO_LARGE,
                            detail="File too large",
                        )
                    f.write(chunk)
            return bytes_written
        except HTTPException:
            try:
                dest.unlink(missing_ok=True)
            except OSError:
                pass
            raise
