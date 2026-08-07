"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Dependency-free liveness and current readiness status.",
    },
    {
        "name": "Service information",
        "description": "Versioned, non-sensitive service identity metadata.",
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an independently configurable FastAPI application."""

    resolved_settings = settings or Settings.from_environment()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("service_started", extra={"event": "service_started"})
        yield
        logger.info("service_stopped", extra={"event": "service_stopped"})

    application = FastAPI(
        title="ShopSphere API Gateway",
        summary="Enterprise API gateway placeholder. Routing, identity integration, policy enforcement, and downstream calls remain future work.",
        description=(
            "Day 1 foundation API only. No database, cache, message broker, "
            "identity provider, authentication, or business workflow is connected."
        ),
        version=resolved_settings.service_version,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_v1_router)
    return application


app = create_app()
