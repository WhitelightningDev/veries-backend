from __future__ import annotations

import os
import tempfile

from fastapi.testclient import TestClient

from veries_backend.app.analytics.noop import NoOpAnalyticsSink
from veries_backend.app.deps import (
    get_analytics_sink,
    get_uploads_service,
    get_verification_assets_service,
    get_verification_session_events_service,
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
from veries_backend.app.services.uploads import UploadsService
from veries_backend.app.services.verification_assets import VerificationAssetsService
from veries_backend.app.services.verification_session_events import (
    VerificationSessionEventsService,
)
from veries_backend.app.services.verification_sessions import VerificationSessionsService
from veries_backend.app.storage.local import LocalObjectStorage


def test_upload_image_persists_asset_and_writes_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app()
        sessions_repo = InMemoryVerificationSessionsRepo()
        assets_repo = InMemoryVerificationAssetsRepo()
        events_repo = InMemoryVerificationSessionEventsRepo()
        analytics = NoOpAnalyticsSink()

        sessions = VerificationSessionsService(repo=sessions_repo, analytics=analytics)
        assets = VerificationAssetsService(sessions=sessions, repo=assets_repo)
        events = VerificationSessionEventsService(
            sessions=sessions, repo=events_repo, analytics=analytics
        )
        uploads = UploadsService(
            sessions=sessions,
            assets=assets,
            events=events,
            storage=LocalObjectStorage(root=tmp),
            images_bucket="",
            videos_bucket="",
            images_prefix="",
            videos_prefix="",
            max_image_upload_bytes=1024,
            max_video_upload_bytes=4096,
        )

        app.dependency_overrides[get_analytics_sink] = lambda: analytics
        app.dependency_overrides[get_verification_sessions_service] = lambda: sessions
        app.dependency_overrides[get_verification_assets_service] = lambda: assets
        app.dependency_overrides[get_verification_session_events_service] = lambda: events
        app.dependency_overrides[get_uploads_service] = lambda: uploads

        client = TestClient(app)
        session_id = client.post("/api/verification-sessions", json={}).json()["id"]

        response = client.post(
            f"/api/verification-sessions/{session_id}/upload",
            data={"customer_id": "cust_123", "asset_type": "id_document"},
            files={"file": ("id.jpg", b"hello", "image/jpeg")},
        )
        assert response.status_code == 201
        asset = response.json()
        assert asset["session_id"] == session_id
        assert asset["asset_type"] == "id_document"
        assert asset["status"] == "uploaded"
        assert asset["storage_path"].startswith("verifications/cust_123/")

        assert os.path.exists(os.path.join(tmp, asset["storage_path"]))


def test_upload_rejects_wrong_mime_for_video() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app()
        sessions_repo = InMemoryVerificationSessionsRepo()
        assets_repo = InMemoryVerificationAssetsRepo()
        events_repo = InMemoryVerificationSessionEventsRepo()
        analytics = NoOpAnalyticsSink()

        sessions = VerificationSessionsService(repo=sessions_repo, analytics=analytics)
        assets = VerificationAssetsService(sessions=sessions, repo=assets_repo)
        events = VerificationSessionEventsService(
            sessions=sessions, repo=events_repo, analytics=analytics
        )
        uploads = UploadsService(
            sessions=sessions,
            assets=assets,
            events=events,
            storage=LocalObjectStorage(root=tmp),
            images_bucket="",
            videos_bucket="",
            images_prefix="",
            videos_prefix="",
            max_image_upload_bytes=1024,
            max_video_upload_bytes=4096,
        )

        app.dependency_overrides[get_uploads_service] = lambda: uploads
        app.dependency_overrides[get_verification_sessions_service] = lambda: sessions
        app.dependency_overrides[get_verification_assets_service] = lambda: assets
        app.dependency_overrides[get_verification_session_events_service] = lambda: events

        client = TestClient(app)
        session_id = client.post("/api/verification-sessions", json={}).json()["id"]

        response = client.post(
            f"/api/verification-sessions/{session_id}/upload",
            data={"customer_id": "cust", "asset_type": "background_video"},
            files={"file": ("video.mp4", b"nope", "image/jpeg")},
        )
        assert response.status_code == 415


def test_upload_rejects_large_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app()
        sessions_repo = InMemoryVerificationSessionsRepo()
        assets_repo = InMemoryVerificationAssetsRepo()
        events_repo = InMemoryVerificationSessionEventsRepo()
        analytics = NoOpAnalyticsSink()

        sessions = VerificationSessionsService(repo=sessions_repo, analytics=analytics)
        assets = VerificationAssetsService(sessions=sessions, repo=assets_repo)
        events = VerificationSessionEventsService(
            sessions=sessions, repo=events_repo, analytics=analytics
        )
        uploads = UploadsService(
            sessions=sessions,
            assets=assets,
            events=events,
            storage=LocalObjectStorage(root=tmp),
            images_bucket="",
            videos_bucket="",
            images_prefix="",
            videos_prefix="",
            max_image_upload_bytes=4,
            max_video_upload_bytes=4096,
        )

        app.dependency_overrides[get_uploads_service] = lambda: uploads
        app.dependency_overrides[get_verification_sessions_service] = lambda: sessions
        app.dependency_overrides[get_verification_assets_service] = lambda: assets
        app.dependency_overrides[get_verification_session_events_service] = lambda: events

        client = TestClient(app)
        session_id = client.post("/api/verification-sessions", json={}).json()["id"]

        response = client.post(
            f"/api/verification-sessions/{session_id}/upload",
            data={"customer_id": "cust", "asset_type": "selfie_with_id"},
            files={"file": ("selfie.png", b"12345", "image/png")},
        )
        assert response.status_code == 413


def test_upload_unknown_session_returns_404() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app()
        sessions_repo = InMemoryVerificationSessionsRepo()
        assets_repo = InMemoryVerificationAssetsRepo()
        events_repo = InMemoryVerificationSessionEventsRepo()
        analytics = NoOpAnalyticsSink()

        sessions = VerificationSessionsService(repo=sessions_repo, analytics=analytics)
        assets = VerificationAssetsService(sessions=sessions, repo=assets_repo)
        events = VerificationSessionEventsService(
            sessions=sessions, repo=events_repo, analytics=analytics
        )
        uploads = UploadsService(
            sessions=sessions,
            assets=assets,
            events=events,
            storage=LocalObjectStorage(root=tmp),
            images_bucket="",
            videos_bucket="",
            images_prefix="",
            videos_prefix="",
            max_image_upload_bytes=1024,
            max_video_upload_bytes=4096,
        )

        app.dependency_overrides[get_uploads_service] = lambda: uploads
        app.dependency_overrides[get_verification_sessions_service] = lambda: sessions
        app.dependency_overrides[get_verification_assets_service] = lambda: assets
        app.dependency_overrides[get_verification_session_events_service] = lambda: events

        client = TestClient(app)
        response = client.post(
            "/api/verification-sessions/00000000-0000-0000-0000-000000000000/upload",
            data={"customer_id": "cust", "asset_type": "id_document"},
            files={"file": ("id.jpg", b"ok", "image/jpeg")},
        )
        assert response.status_code == 404
