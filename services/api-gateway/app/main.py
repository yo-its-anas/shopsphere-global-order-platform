"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.application.customer_proxy import CustomerServiceProxy
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.infrastructure.http_client import ConfiguredHttpClient, UpstreamHttpClient

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
    {
        "name": "Customer capability",
        "description": (
            "Transport-only routes to customer-service. Customer-service validates JWTs, "
            "enforces roles and ownership, and owns all customer domain behavior."
        ),
    },
]


def create_app(
    settings: Settings | None = None,
    *,
    customer_service_client: UpstreamHttpClient | None = None,
) -> FastAPI:
    """Create an independently configurable FastAPI application."""

    resolved_settings = settings or Settings.from_environment()
    configure_logging(resolved_settings.log_level)
    owns_customer_client = customer_service_client is None
    resolved_customer_client = customer_service_client or ConfiguredHttpClient(
        resolved_settings.customer_service_url,
        resolved_settings.customer_service_timeout_seconds,
    )
    customer_service_proxy = CustomerServiceProxy(resolved_customer_client)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("service_started", extra={"event": "service_started"})
        yield
        if owns_customer_client:
            await resolved_customer_client.aclose()
        logger.info("service_stopped", extra={"event": "service_stopped"})

    application = FastAPI(
        title="ShopSphere API Gateway",
        summary="Versioned ShopSphere API entry point with customer capability routing.",
        description=(
            "Routes authenticated customer traffic to customer-service without implementing "
            "customer domain logic. Bearer tokens are propagated for authoritative downstream "
            "validation and are never written to gateway logs."
        ),
        version=resolved_settings.service_version,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.customer_service_proxy = customer_service_proxy
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_v1_router)
    return application


app = create_app()
