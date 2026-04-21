from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from veries_backend.app.analytics.noop import NoOpAnalyticsSink
from veries_backend.app.deps import get_verification_sessions_service
from veries_backend.app.domain.verification_sessions.events import VerificationSessionEventType
from veries_backend.app.infra.verification_session_events_in_memory import (
    InMemoryVerificationSessionEventsRepo,
)
from veries_backend.app.infra.verification_sessions_in_memory import (
    InMemoryVerificationSessionsRepo,
)
from veries_backend.app.main import create_app
from veries_backend.app.services.verification_sessions import VerificationSessionsService


def test_verification_session_create_get_patch_flow() -> None:
    app = create_app()
    repo = InMemoryVerificationSessionsRepo()
    events_repo = InMemoryVerificationSessionEventsRepo()
    app.dependency_overrides[get_verification_sessions_service] = lambda: (
        VerificationSessionsService(
            repo=repo, analytics=NoOpAnalyticsSink(), events_repo=events_repo
        )
    )
    client = TestClient(app)

    create_response = client.post("/api/verification-sessions", json={})
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "started"
    assert created["id"]

    session_id = created["id"]
    session_uuid = UUID(session_id)
    events = events_repo.list_for_session(session_uuid)
    assert any(e.event_type == VerificationSessionEventType.SESSION_STARTED for e in events)

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
    events_repo = InMemoryVerificationSessionEventsRepo()
    app.dependency_overrides[get_verification_sessions_service] = lambda: (
        VerificationSessionsService(
            repo=repo, analytics=NoOpAnalyticsSink(), events_repo=events_repo
        )
    )
    client = TestClient(app)

    create_response = client.post("/api/verification-sessions", json={})
    session_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/verification-sessions/{session_id}", json={"status": "completed"}
    )
    assert patch_response.status_code == 409


def test_verification_session_status_change_emits_lifecycle_events_without_duplicates() -> None:
    app = create_app()
    repo = InMemoryVerificationSessionsRepo()
    events_repo = InMemoryVerificationSessionEventsRepo()
    app.dependency_overrides[get_verification_sessions_service] = lambda: (
        VerificationSessionsService(
            repo=repo, analytics=NoOpAnalyticsSink(), events_repo=events_repo
        )
    )
    client = TestClient(app)

    session_id = client.post("/api/verification-sessions", json={}).json()["id"]
    session_uuid = UUID(session_id)

    client.patch(f"/api/verification-sessions/{session_id}", json={"status": "dropped_off"})
    client.patch(f"/api/verification-sessions/{session_id}", json={"status": "resumed"})
    client.patch(f"/api/verification-sessions/{session_id}", json={"status": "submitted"})
    client.patch(f"/api/verification-sessions/{session_id}", json={"status": "completed"})

    types = [e.event_type for e in events_repo.list_for_session(session_uuid)]
    assert VerificationSessionEventType.SESSION_STARTED in types
    assert VerificationSessionEventType.DROP_OFF in types
    assert VerificationSessionEventType.RESUME in types
    assert VerificationSessionEventType.SUBMISSION_CONFIRMED in types
    assert VerificationSessionEventType.COMPLETED in types

    count_before = len(types)
    client.patch(f"/api/verification-sessions/{session_id}", json={"status": "completed"})
    count_after = len(events_repo.list_for_session(session_uuid))
    assert count_after == count_before
