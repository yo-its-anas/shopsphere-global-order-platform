"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.routing import compile_path

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.v1.router import api_v1_router
from app.application.dashboard import DashboardService
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics import AnalyticsMetrics
from app.core.middleware import CorrelationIdMiddleware
from app.core.security import KeycloakTokenVerifier, TokenVerifier
from app.core.telemetry import Telemetry, configure_telemetry
from app.infrastructure.prometheus_adapter import PrometheusAdapter
from app.infrastructure.service_clients import DashboardSources, HttpDashboardSources

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
        "name": "Executive operations dashboard",
        "description": (
            "Authorized read-only aggregation of source-owned ShopSphere business KPIs."
        ),
    },
    {
        "name": "Observability",
        "description": "Internal bounded metrics exposition.",
    },
]


def create_app(
    settings: Settings | None = None,
    *,
    telemetry: Telemetry | None = None,
    token_verifier: TokenVerifier | None = None,
    dashboard_sources: DashboardSources | None = None,
) -> FastAPI:
    """Create an independently configurable FastAPI application."""

    resolved_settings = settings or Settings.from_environment()
    configure_logging(
        resolved_settings.log_level,
        resolved_settings.service_name,
        resolved_settings.service_version,
        resolved_settings.environment,
    )
    owns_telemetry = telemetry is None
    resolved_telemetry = telemetry or configure_telemetry(
        resolved_settings.service_name,
        resolved_settings.service_version,
        resolved_settings.environment,
    )
    metrics = AnalyticsMetrics(
        resolved_settings.service_name,
        resolved_settings.service_version,
        resolved_settings.environment,
    )
    resolved_sources = dashboard_sources or HttpDashboardSources(
        resolved_settings, telemetry=resolved_telemetry
    )
    prometheus_adapter = PrometheusAdapter(resolved_settings)
    resolved_verifier = token_verifier
    if resolved_verifier is None and resolved_settings.keycloak_issuer:
        resolved_verifier = KeycloakTokenVerifier(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("service_started", extra={"event": "service_started"})
        yield
        await resolved_sources.aclose()
        await prometheus_adapter.aclose()
        logger.info("service_stopped", extra={"event": "service_stopped"})
        if owns_telemetry:
            resolved_telemetry.shutdown()

    application = FastAPI(
        title="ShopSphere Analytics Service",
        summary="Read-only executive business operations aggregation boundary.",
        description=(
            "Aggregates real persisted PoC data through fixed existing domain-service APIs. "
            "Customer, Catalogue/Inventory, and Order services retain authority."
        ),
        version=resolved_settings.service_version,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.telemetry = resolved_telemetry
    application.state.metrics = metrics
    application.state.token_verifier = resolved_verifier
    application.state.dashboard_sources = resolved_sources
    application.state.dashboard_service = DashboardService(resolved_sources, metrics)
    application.state.prometheus_adapter = prometheus_adapter
    application.add_middleware(CorrelationIdMiddleware)
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
