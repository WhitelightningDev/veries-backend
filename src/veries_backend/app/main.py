from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from veries_backend.app.api.router import api_router
from veries_backend.app.core.config import get_settings
from veries_backend.app.core.lifespan import lifespan
from veries_backend.app.core.logging import configure_logging

logger = logging.getLogger("veries_backend")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    if settings.cors_origins:
        allow_credentials = settings.cors_allow_credentials
        if allow_credentials and "*" in settings.cors_origins:
            logger.warning("CORS: disabling credentials because CORS_ORIGINS includes '*'")
            allow_credentials = False
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
