from __future__ import annotations

from fastapi.testclient import TestClient

from veries_backend.app.main import create_app


def test_health() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
