from __future__ import annotations

from fastapi.testclient import TestClient

from veries_backend.app.analytics.noop import NoOpAnalyticsSink
from veries_backend.app.deps import (
    get_analytics_sink,
    get_verification_session_events_service,
    get_verification_sessions_service,
)
from veries_backend.app.infra.verification_session_events_in_memory import (
    InMemoryVerificationSessionEventsRepo,
)
from veries_backend.app.infra.verification_sessions_in_memory import (
    InMemoryVerificationSessionsRepo,
)
from veries_backend.app.main import create_app
from veries_backend.app.services.verification_session_events import (
    VerificationSessionEventsService,
)
from veries_backend.app.services.verification_sessions import VerificationSessionsService


def test_log_event_returns_201() -> None:
    app = create_app()
    sessions_repo = InMemoryVerificationSessionsRepo()
    events_repo = InMemoryVerificationSessionEventsRepo()
    analytics = NoOpAnalyticsSink()

    sessions = VerificationSessionsService(
        repo=sessions_repo, analytics=analytics, events_repo=events_repo
    )
    app.dependency_overrides[get_analytics_sink] = lambda: analytics
    app.dependency_overrides[get_verification_sessions_service] = lambda: sessions
    app.dependency_overrides[get_verification_session_events_service] = lambda: (
        VerificationSessionEventsService(
            sessions=sessions,
            repo=events_repo,
            analytics=analytics,
        )
    )

    client = TestClient(app)
    session_id = client.post("/api/verification-sessions", json={}).json()["id"]

    response = client.post(
        f"/api/verification-sessions/{session_id}/events",
        json={"event_type": "camera_opened", "metadata": {"source": "web"}},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["session_id"] == session_id
    assert body["event_type"] == "camera_opened"
    assert body["metadata"] == {"source": "web"}

    list_response = client.get(f"/api/verification-sessions/{session_id}/events")
    assert list_response.status_code == 200
    events = list_response.json()
    assert any(e["event_type"] == "camera_opened" for e in events)


def test_log_event_unknown_session_returns_404() -> None:
    app = create_app()
    sessions_repo = InMemoryVerificationSessionsRepo()
    events_repo = InMemoryVerificationSessionEventsRepo()
    analytics = NoOpAnalyticsSink()

    sessions = VerificationSessionsService(
        repo=sessions_repo, analytics=analytics, events_repo=events_repo
    )
    app.dependency_overrides[get_analytics_sink] = lambda: analytics
    app.dependency_overrides[get_verification_sessions_service] = lambda: sessions
    app.dependency_overrides[get_verification_session_events_service] = lambda: (
        VerificationSessionEventsService(
            sessions=sessions,
            repo=events_repo,
            analytics=analytics,
        )
    )

    client = TestClient(app)
    response = client.post(
        "/api/verification-sessions/00000000-0000-0000-0000-000000000000/events",
        json={"event_type": "camera_opened"},
    )
    assert response.status_code == 404

    list_response = client.get(
        "/api/verification-sessions/00000000-0000-0000-0000-000000000000/events"
    )
    assert list_response.status_code == 404
