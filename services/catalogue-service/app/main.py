"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.application.catalogue import UnitOfWorkFactory
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.core.security import KeycloakTokenVerifier, TokenVerifier
from app.infrastructure.database import (
    create_database_engine,
    create_session_factory,
    database_is_ready,
)
from app.infrastructure.repositories import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)
DatabaseReadinessChecker = Callable[[AsyncEngine | None], Awaitable[bool]]

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
        "name": "Catalogue queries",
        "description": "Authenticated role-aware category, product, search, and pricing reads.",
    },
    {
        "name": "Catalogue administration",
        "description": "Operations-administrator product, category, lifecycle, and pricing commands.",
    },
    {
        "name": "Inventory availability",
        "description": "Customer-safe derived product availability.",
    },
    {
        "name": "Inventory operations",
        "description": "Support and operations inventory balances, movements, and statistics.",
    },
    {
        "name": "Inventory administration",
        "description": "Auditable operations-administrator stock commands and settings.",
    },
]


def create_app(
    settings: Settings | None = None,
    *,
    database_engine: AsyncEngine | None = None,
    token_verifier: TokenVerifier | None = None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
    database_readiness_checker: DatabaseReadinessChecker = database_is_ready,
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
    resolved_unit_of_work_factory = unit_of_work_factory
    if resolved_unit_of_work_factory is None and resolved_engine is not None:
        resolved_session_factory = create_session_factory(resolved_engine)

        def build_unit_of_work() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(resolved_session_factory)

        resolved_unit_of_work_factory = build_unit_of_work

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("service_started", extra={"event": "service_started"})
        yield
        if resolved_engine is not None:
            await resolved_engine.dispose()
        logger.info("service_stopped", extra={"event": "service_stopped"})

    application = FastAPI(
        title="ShopSphere Catalogue Service",
        summary="Product catalogue, effective pricing, and transactional inventory management.",
        description=(
            "Keycloak-authenticated Product Catalogue and Inventory APIs backed by PostgreSQL. "
            "Availability is derived and stock changes retain append-only movement evidence. "
            "Order reservation behavior remains outside this implementation."
        ),
        version=resolved_settings.service_version,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database_engine = resolved_engine
    application.state.database_readiness_checker = database_readiness_checker
    application.state.token_verifier = resolved_verifier
    application.state.unit_of_work_factory = resolved_unit_of_work_factory
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_v1_router)
    return application


app = create_app()
