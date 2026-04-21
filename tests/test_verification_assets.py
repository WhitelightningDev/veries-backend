from __future__ import annotations

import re

from fastapi.testclient import TestClient

from veries_backend.app.analytics.noop import NoOpAnalyticsSink
from veries_backend.app.deps import (
    get_analytics_sink,
    get_verification_assets_service,
    get_verification_sessions_service,
)
from veries_backend.app.infra.verification_assets_in_memory import InMemoryVerificationAssetsRepo
from veries_backend.app.infra.verification_session_events_in_memory import (
    InMemoryVerificationSessionEventsRepo,
)
from veries_backend.app.infra.verification_sessions_in_memory import (
    InMemoryVerificationSessionsRepo,
)
from veries_backend.app.main import create_app
from veries_backend.app.services.verification_assets import VerificationAssetsService
from veries_backend.app.services.verification_sessions import VerificationSessionsService


def test_create_and_list_assets() -> None:
    app = create_app()
    sessions_repo = InMemoryVerificationSessionsRepo()
    assets_repo = InMemoryVerificationAssetsRepo()
    events_repo = InMemoryVerificationSessionEventsRepo()
    analytics = NoOpAnalyticsSink()

    app.dependency_overrides[get_analytics_sink] = lambda: analytics
    app.dependency_overrides[get_verification_sessions_service] = lambda: (
        VerificationSessionsService(
            repo=sessions_repo, analytics=analytics, events_repo=events_repo
        )
    )
    app.dependency_overrides[get_verification_assets_service] = lambda: VerificationAssetsService(
        sessions=VerificationSessionsService(
            repo=sessions_repo, analytics=analytics, events_repo=events_repo
        ),
        repo=assets_repo,
    )

    client = TestClient(app)
    session_id = client.post("/api/verification-sessions", json={}).json()["id"]

    create_response = client.post(
        f"/api/verification-sessions/{session_id}/assets",
        json={
            "customer_id": "cust_123",
            "asset_type": "id_document",
            "mime_type": "image/jpeg",
        },
    )
    assert create_response.status_code == 201
    asset = create_response.json()
    assert asset["session_id"] == session_id
    assert asset["asset_type"] == "id_document"
    assert asset["status"] == "pending"
    assert re.match(
        rf"^verifications/cust_123/verification-sessions/{session_id}/id_document/.+\.jpg$",
        asset["storage_path"],
    )

    list_response = client.get(f"/api/verification-sessions/{session_id}/assets")
    assert list_response.status_code == 200
    assets = list_response.json()
    assert len(assets) == 1
    assert assets[0]["id"] == asset["id"]


def test_asset_patch_uploaded_sets_uploaded_at() -> None:
    app = create_app()
    sessions_repo = InMemoryVerificationSessionsRepo()
    assets_repo = InMemoryVerificationAssetsRepo()
    events_repo = InMemoryVerificationSessionEventsRepo()
    analytics = NoOpAnalyticsSink()

    app.dependency_overrides[get_analytics_sink] = lambda: analytics
    app.dependency_overrides[get_verification_sessions_service] = lambda: (
        VerificationSessionsService(
            repo=sessions_repo, analytics=analytics, events_repo=events_repo
        )
    )
    app.dependency_overrides[get_verification_assets_service] = lambda: VerificationAssetsService(
        sessions=VerificationSessionsService(
            repo=sessions_repo, analytics=analytics, events_repo=events_repo
        ),
        repo=assets_repo,
    )

    client = TestClient(app)
    session_id = client.post("/api/verification-sessions", json={}).json()["id"]
    asset_id = client.post(
        f"/api/verification-sessions/{session_id}/assets",
        json={"customer_id": "cust", "asset_type": "background_video", "mime_type": "video/mp4"},
    ).json()["id"]

    patch_response = client.patch(
        f"/api/verification-assets/{asset_id}", json={"status": "uploaded"}
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["status"] == "uploaded"
    assert body["uploaded_at"] is not None


def test_asset_uploaded_at_without_uploaded_status_returns_409() -> None:
    app = create_app()
    sessions_repo = InMemoryVerificationSessionsRepo()
    assets_repo = InMemoryVerificationAssetsRepo()
    events_repo = InMemoryVerificationSessionEventsRepo()
    analytics = NoOpAnalyticsSink()

    app.dependency_overrides[get_analytics_sink] = lambda: analytics
    app.dependency_overrides[get_verification_sessions_service] = lambda: (
        VerificationSessionsService(
            repo=sessions_repo, analytics=analytics, events_repo=events_repo
        )
    )
    app.dependency_overrides[get_verification_assets_service] = lambda: VerificationAssetsService(
        sessions=VerificationSessionsService(
            repo=sessions_repo, analytics=analytics, events_repo=events_repo
        ),
        repo=assets_repo,
    )

    client = TestClient(app)
    session_id = client.post("/api/verification-sessions", json={}).json()["id"]
    asset_id = client.post(
        f"/api/verification-sessions/{session_id}/assets",
        json={"customer_id": "cust", "asset_type": "selfie_with_id", "mime_type": "image/png"},
    ).json()["id"]

    patch_response = client.patch(
        f"/api/verification-assets/{asset_id}",
        json={"uploaded_at": "2026-01-01T00:00:00Z"},
    )
    assert patch_response.status_code == 409
