from __future__ import annotations

from threading import Lock
from uuid import UUID

from veries_backend.app.domain.verification_assets.model import VerificationAsset
from veries_backend.app.domain.verification_assets.repo import VerificationAssetsRepo


class InMemoryVerificationAssetsRepo(VerificationAssetsRepo):
    def __init__(self) -> None:
        self._lock = Lock()
        self._assets: dict[UUID, VerificationAsset] = {}
        self._assets_by_session: dict[UUID, list[UUID]] = {}

    def create(self, asset: VerificationAsset) -> VerificationAsset:
        with self._lock:
            self._assets[asset.id] = asset
            self._assets_by_session.setdefault(asset.session_id, []).append(asset.id)
            return asset

    def get(self, asset_id: UUID) -> VerificationAsset | None:
        with self._lock:
            return self._assets.get(asset_id)

    def update(self, asset: VerificationAsset) -> VerificationAsset:
        with self._lock:
            self._assets[asset.id] = asset
            return asset

    def list_for_session(self, session_id: UUID) -> list[VerificationAsset]:
        with self._lock:
            ids = list(self._assets_by_session.get(session_id, []))
            return [self._assets[asset_id] for asset_id in ids if asset_id in self._assets]


in_memory_verification_assets_repo = InMemoryVerificationAssetsRepo()
