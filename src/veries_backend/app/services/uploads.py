from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Final
from uuid import UUID

from fastapi import HTTPException, UploadFile
from fastapi import status as http_status

from veries_backend.app.domain.verification_assets.status import VerificationAssetStatus
from veries_backend.app.domain.verification_assets.types import VerificationAssetType
from veries_backend.app.domain.verification_sessions.events import VerificationSessionEventType
from veries_backend.app.services.asset_vision import AssetVisionService
from veries_backend.app.services.verification_assets import VerificationAssetsService
from veries_backend.app.services.verification_session_events import VerificationSessionEventsService
from veries_backend.app.services.verification_sessions import VerificationSessionsService
from veries_backend.app.storage.base import ObjectStorage
from veries_backend.app.storage.errors import (
    StorageDependencyMissingError,
    StorageNotConfiguredError,
    StorageObjectTooLargeError,
)

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
        vision: AssetVisionService | None = None,
        storage: ObjectStorage,
        images_bucket: str,
        videos_bucket: str,
        images_prefix: str,
        videos_prefix: str,
        max_image_upload_bytes: int,
        max_video_upload_bytes: int,
    ) -> None:
        self._sessions = sessions
        self._assets = assets
        self._events = events
        self._vision = vision
        self._storage = storage
        self._images_bucket = images_bucket
        self._videos_bucket = videos_bucket
        self._images_prefix = images_prefix.strip("/")
        self._videos_prefix = videos_prefix.strip("/")
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

        vision_result: dict | None = None
        upload_stream = file.file

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

        try:
            if (
                self._vision is not None
                and self._vision.enabled
                and asset_type != VerificationAssetType.BACKGROUND_VIDEO
                and mime_type in _IMAGE_MIME_TYPES
            ):
                data = _read_limited(file.file, self._max_bytes_for(asset_type))
                vision_result = self._vision.analyze_upload(
                    asset_type=asset_type,
                    mime_type=mime_type,
                    data=data,
                )
                if vision_result.get("should_reject"):
                    raise HTTPException(
                        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "message": "Upload rejected by vision checks",
                            "vision": vision_result,
                        },
                    )
                upload_stream = BytesIO(data)

            bucket, object_name = self._bucket_and_object_name(asset_type, asset.storage_path)
            bytes_written = self._storage.put_stream(
                bucket=bucket,
                object_name=object_name,
                content_type=mime_type,
                stream=upload_stream,
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
                    **({"vision": vision_result} if vision_result is not None else {}),
                },
            )
            return UploadResult(
                asset_id=asset.id,
                storage_path=asset.storage_path,
                bytes_written=bytes_written,
            )
        except StorageObjectTooLargeError as exc:
            raise HTTPException(
                status_code=http_status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File too large",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage path",
            ) from exc
        except StorageNotConfiguredError as exc:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage is not configured",
            ) from exc
        except StorageDependencyMissingError as exc:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc
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

    def _bucket_and_object_name(
        self, asset_type: VerificationAssetType, storage_path: str
    ) -> tuple[str, str]:
        if asset_type == VerificationAssetType.BACKGROUND_VIDEO:
            prefix = self._videos_prefix
            bucket = self._videos_bucket
        else:
            prefix = self._images_prefix
            bucket = self._images_bucket

        object_name = f"{prefix}/{storage_path}" if prefix else storage_path
        return bucket, object_name

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
        if asset_type in {
            VerificationAssetType.ID_DOCUMENT,
            VerificationAssetType.ID_DOCUMENT_FRONT,
            VerificationAssetType.ID_DOCUMENT_BACK,
        }:
            allowed |= _ID_DOC_EXTRA_MIME_TYPES

        if mime_type not in allowed:
            raise HTTPException(
                status_code=http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Invalid image/document content-type",
            )


def _read_limited(stream, max_bytes: int) -> bytes:
    data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise StorageObjectTooLargeError()
    return data
