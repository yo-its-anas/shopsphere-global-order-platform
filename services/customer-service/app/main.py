"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.core.security import KeycloakTokenVerifier, TokenVerifier
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.repositories import SqlAlchemyUnitOfWork

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
        "name": "Customer self-service",
        "description": "Authenticated profile, address, and activity operations scoped to the token subject.",
    },
    {
        "name": "Customer administration",
        "description": "Read-only support access and explicitly governed operations administration.",
    },
]


def create_app(
    settings: Settings | None = None,
    *,
    database_engine: AsyncEngine | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Create an independently configurable FastAPI application."""

    resolved_settings = settings or Settings.from_environment()
    configure_logging(resolved_settings.log_level)
    resolved_engine = database_engine
    if resolved_engine is None and resolved_settings.database_url:
        resolved_engine = create_database_engine(
            resolved_settings.database_url,
            resolved_settings.database_connect_timeout_seconds,
        )
    resolved_verifier = token_verifier
    if resolved_verifier is None and resolved_settings.keycloak_issuer:
        resolved_verifier = KeycloakTokenVerifier(resolved_settings)
    resolved_session_factory = (
        create_session_factory(resolved_engine) if resolved_engine is not None else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("service_started", extra={"event": "service_started"})
        yield
        if resolved_engine is not None:
            await resolved_engine.dispose()
        logger.info("service_stopped", extra={"event": "service_stopped"})

    application = FastAPI(
        title="ShopSphere Customer Service",
        summary="Customer profiles, addresses, account status, and customer-domain audit history.",
        description=(
            "Keycloak-authenticated customer business APIs. Keycloak remains the exclusive "
            "credential authority; this service never receives or stores passwords."
        ),
        version=resolved_settings.service_version,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database_engine = resolved_engine
    application.state.token_verifier = resolved_verifier
    application.state.unit_of_work_factory = (
        (lambda: SqlAlchemyUnitOfWork(resolved_session_factory))
        if resolved_session_factory is not None
        else None
    )
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_v1_router)
    return application


app = create_app()
