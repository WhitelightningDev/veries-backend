from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from veries_backend.app.storage.errors import StorageObjectTooLargeError

_CHUNK_SIZE: Final[int] = 1024 * 1024


class LocalObjectStorage:
    def __init__(self, *, root: str) -> None:
        self._root = Path(root)

    def put_stream(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
        stream,
        max_bytes: int,
    ) -> int:
        dest = self._safe_dest_path(object_name)
        dest.parent.mkdir(parents=True, exist_ok=True)

        bytes_written = 0
        try:
            with dest.open("wb") as f:
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
                dest.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _safe_dest_path(self, object_name: str) -> Path:
        root = self._root.resolve()
        dest = (root / object_name).resolve()
        if os.path.commonpath([str(root), str(dest)]) != str(root):
            raise ValueError("Invalid object name")
        return dest
