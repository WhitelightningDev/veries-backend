from __future__ import annotations

from typing import Final

from veries_backend.app.storage.errors import (
    StorageDependencyMissingError,
    StorageNotConfiguredError,
    StorageObjectTooLargeError,
)

_CHUNK_SIZE: Final[int] = 1024 * 1024


class GCSObjectStorage:
    def __init__(
        self,
        *,
        project: str | None,
        credentials_path: str | None,
    ) -> None:
        self._project = project
        self._credentials_path = credentials_path
        self._client = self._create_client()

    def _create_client(self):
        try:
            from google.cloud import storage  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise StorageDependencyMissingError(
                "google-cloud-storage is not installed. Install with `pip install -e '.[gcp]'`."
            ) from exc

        if self._credentials_path:
            return storage.Client.from_service_account_json(
                self._credentials_path, project=self._project
            )
        return storage.Client(project=self._project)

    def put_stream(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
        stream,
        max_bytes: int,
    ) -> int:
        if not bucket:
            raise StorageNotConfiguredError("GCS bucket is required")

        bkt = self._client.bucket(bucket)
        blob = bkt.blob(object_name)
        blob.content_type = content_type or None

        bytes_written = 0
        writer = blob.open("wb")  # resumable for larger payloads
        try:
            with writer as f:
                while True:
                    chunk = stream.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise StorageObjectTooLargeError()
                    f.write(chunk)
            return bytes_written
        except StorageObjectTooLargeError:
            try:
                blob.delete()
            except Exception:
                pass
            raise
