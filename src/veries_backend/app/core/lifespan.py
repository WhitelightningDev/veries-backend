from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger("veries_backend")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("startup")
    try:
        from veries_backend.app.core.config import get_settings
        from veries_backend.app.deps import get_analytics_sink

        settings = get_settings()
        if settings.bigquery_enabled and settings.bigquery_validate_on_startup:
            sink = get_analytics_sink()
            validate = getattr(sink, "validate_on_startup", None)
            if callable(validate):
                validate()
    except Exception as exc:
        try:
            from veries_backend.app.core.config import get_settings

            if get_settings().bigquery_fail_requests:
                raise
        except ImportError:
            # If settings can't be read, default to non-blocking.
            pass
        logger.warning("startup check failed (continuing): %s", exc)
    yield
    try:
        from veries_backend.app.deps import get_analytics_sink

        sink = get_analytics_sink()
        close = getattr(sink, "close", None)
        if callable(close):
            close()
    except Exception:
        pass
    logger.info("shutdown")
