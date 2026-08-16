"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import compile_path

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.v1.router import api_v1_router
from app.application.analytics_proxy import AnalyticsServiceProxy
from app.application.catalogue_proxy import CatalogueServiceProxy
from app.application.customer_proxy import CustomerServiceProxy
from app.application.order_proxy import OrderServiceProxy
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics import ServiceMetrics
from app.core.middleware import CorrelationIdMiddleware
from app.core.telemetry import Telemetry, configure_telemetry
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
    {
        "name": "Catalogue capability",
        "description": (
            "Transport-only routes to catalogue-service. Catalogue-service validates JWTs "
            "and authoritatively enforces catalogue and inventory roles."
        ),
    },
    {
        "name": "Order capability",
        "description": (
            "Transport-only routes to order-service. Order-service validates JWTs and "
            "authoritatively enforces cart ownership, order roles, lifecycle, and idempotency."
        ),
    },
]


def create_app(
    settings: Settings | None = None,
    *,
    telemetry: Telemetry | None = None,
    customer_service_client: UpstreamHttpClient | None = None,
    catalogue_service_client: UpstreamHttpClient | None = None,
    order_service_client: UpstreamHttpClient | None = None,
    analytics_service_client: UpstreamHttpClient | None = None,
) -> FastAPI:
    """Create an independently configurable FastAPI application."""

    resolved_settings = settings or Settings.from_environment()
    configure_logging(resolved_settings.log_level)
    owns_telemetry = telemetry is None
    resolved_telemetry = telemetry or configure_telemetry(
        resolved_settings.service_name,
        resolved_settings.service_version,
        resolved_settings.environment,
    )
    metrics = ServiceMetrics(
        resolved_settings.service_name,
        resolved_settings.service_version,
        resolved_settings.environment,
    )
    owns_customer_client = customer_service_client is None
    resolved_customer_client = customer_service_client or ConfiguredHttpClient(
        resolved_settings.customer_service_url,
        resolved_settings.customer_service_timeout_seconds,
        resolved_telemetry,
        "customer-service",
    )
    customer_service_proxy = CustomerServiceProxy(resolved_customer_client, metrics)
    owns_catalogue_client = catalogue_service_client is None
    resolved_catalogue_client = catalogue_service_client or ConfiguredHttpClient(
        resolved_settings.catalogue_service_url,
        resolved_settings.catalogue_service_timeout_seconds,
        resolved_telemetry,
        "catalogue-service",
    )
    catalogue_service_proxy = CatalogueServiceProxy(resolved_catalogue_client, metrics)
    owns_order_client = order_service_client is None
    resolved_order_client = order_service_client or ConfiguredHttpClient(
        resolved_settings.order_service_url,
        resolved_settings.order_service_timeout_seconds,
        resolved_telemetry,
        "order-service",
    )
    order_service_proxy = OrderServiceProxy(resolved_order_client, metrics)
    owns_analytics_client = analytics_service_client is None
    resolved_analytics_client = analytics_service_client or ConfiguredHttpClient(
        resolved_settings.analytics_service_url,
        resolved_settings.analytics_service_timeout_seconds,
        resolved_telemetry,
        "analytics-service",
    )
    analytics_service_proxy = AnalyticsServiceProxy(resolved_analytics_client, metrics)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("service_started", extra={"event": "service_started"})
        yield
        if owns_customer_client:
            await resolved_customer_client.aclose()
        if owns_catalogue_client:
            await resolved_catalogue_client.aclose()
        if owns_order_client:
            await resolved_order_client.aclose()
        if owns_analytics_client:
            await resolved_analytics_client.aclose()
        logger.info("service_stopped", extra={"event": "service_stopped"})
        if owns_telemetry:
            resolved_telemetry.shutdown()

    application = FastAPI(
        title="ShopSphere API Gateway",
        summary="Versioned ShopSphere API entry point for customer, catalogue, and order APIs.",
        description=(
            "Routes authenticated traffic to fixed customer, catalogue, and order upstreams without "
            "implementing domain logic. Bearer tokens are propagated for authoritative "
            "downstream validation and are never written to gateway logs."
        ),
        version=resolved_settings.service_version,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.telemetry = resolved_telemetry
    application.state.metrics = metrics
    application.state.customer_service_proxy = customer_service_proxy
    application.state.catalogue_service_proxy = catalogue_service_proxy
    application.state.order_service_proxy = order_service_proxy
    application.state.analytics_service_proxy = analytics_service_proxy
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID"],
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(metrics_router)
    application.include_router(api_v1_router)
    metric_paths = ("/metrics", *application.openapi()["paths"])
    application.state.metric_route_patterns = tuple(
        (path, compile_path(path)[0]) for path in metric_paths
    )
    resolved_telemetry.instrument_app(application)
    return application


app = create_app()
