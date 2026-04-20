from __future__ import annotations

from typing import Protocol
from uuid import UUID

from veries_backend.app.domain.verification_assets.model import VerificationAsset


class VerificationAssetsRepo(Protocol):
    def create(self, asset: VerificationAsset) -> VerificationAsset: ...

    def get(self, asset_id: UUID) -> VerificationAsset | None: ...

    def update(self, asset: VerificationAsset) -> VerificationAsset: ...

    def list_for_session(self, session_id: UUID) -> list[VerificationAsset]: ...
