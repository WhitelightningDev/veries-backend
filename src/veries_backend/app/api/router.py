from __future__ import annotations

from fastapi import APIRouter

from veries_backend.app.api.routes.health import router as health_router
from veries_backend.app.api.routes.verification_assets import router as verification_assets_router
from veries_backend.app.api.routes.verification_session_events import (
    router as verification_session_events_router,
)
from veries_backend.app.api.routes.verification_sessions import (
    router as verification_sessions_router,
)

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(verification_sessions_router, tags=["verification-sessions"])
api_router.include_router(verification_session_events_router, tags=["verification-session-events"])
api_router.include_router(verification_assets_router, tags=["verification-assets"])
