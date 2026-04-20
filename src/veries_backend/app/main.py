from __future__ import annotations

from fastapi import FastAPI

from veries_backend.app.api.router import api_router
from veries_backend.app.core.config import get_settings
from veries_backend.app.core.lifespan import lifespan
from veries_backend.app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
