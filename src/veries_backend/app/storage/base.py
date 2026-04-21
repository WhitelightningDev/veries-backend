from __future__ import annotations

from typing import BinaryIO, Protocol


class ObjectStorage(Protocol):
    def put_stream(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
        stream: BinaryIO,
        max_bytes: int,
    ) -> int:
        """Write stream to storage. Returns bytes written."""
