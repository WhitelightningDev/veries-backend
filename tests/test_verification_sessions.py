from __future__ import annotations

from fastapi.testclient import TestClient

from veries_backend.app.analytics.noop import NoOpAnalyticsSink
from veries_backend.app.deps import get_verification_sessions_service
from veries_backend.app.infra.verification_sessions_in_memory import (
    InMemoryVerificationSessionsRepo,
)
from veries_backend.app.main import create_app
from veries_backend.app.services.verification_sessions import VerificationSessionsService


def test_verification_session_create_get_patch_flow() -> None:
    app = create_app()
    repo = InMemoryVerificationSessionsRepo()
    app.dependency_overrides[get_verification_sessions_service] = lambda: (
        VerificationSessionsService(repo=repo, analytics=NoOpAnalyticsSink())
    )
    client = TestClient(app)

    create_response = client.post("/api/verification-sessions", json={})
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "started"
    assert created["id"]

    session_id = created["id"]

    get_response = client.get(f"/api/verification-sessions/{session_id}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["id"] == session_id
    assert fetched["status"] == "started"

    patch_response = client.patch(
        f"/api/verification-sessions/{session_id}", json={"status": "in_progress"}
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["status"] == "in_progress"


def test_verification_session_invalid_transition_returns_409() -> None:
    app = create_app()
    repo = InMemoryVerificationSessionsRepo()
    app.dependency_overrides[get_verification_sessions_service] = lambda: (
        VerificationSessionsService(repo=repo, analytics=NoOpAnalyticsSink())
    )
    client = TestClient(app)

    create_response = client.post("/api/verification-sessions", json={})
    session_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/verification-sessions/{session_id}", json={"status": "completed"}
    )
    assert patch_response.status_code == 409
