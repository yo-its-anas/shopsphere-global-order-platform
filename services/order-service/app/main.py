"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.core.security import KeycloakTokenVerifier, TokenVerifier
from app.domain.repositories import CatalogueProductProvider, UnitOfWork
from app.infrastructure.catalogue_client import CatalogueHttpClient, KeycloakServiceTokenProvider
from app.infrastructure.database import (
    create_database_engine,
    create_session_factory,
    database_is_ready,
)
from app.infrastructure.repositories import SqlAlchemyOrderOutboxStore, SqlAlchemyUnitOfWork

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
        "name": "Customer shopping cart",
        "description": (
            "Authenticated, subject-owned cart operations with non-authoritative "
            "catalogue display snapshots."
        ),
    },
    {
        "name": "Order checkout",
        "description": (
            "Idempotent checkout, actor-scoped history, safe audit visibility, and "
            "controlled lifecycle commands."
        ),
    },
]


def create_app(
    settings: Settings | None = None,
    *,
    database_engine: AsyncEngine | None = None,
    token_verifier: TokenVerifier | None = None,
    catalogue_client: CatalogueProductProvider | None = None,
    unit_of_work_factory: Callable[[], UnitOfWork] | None = None,
    readiness_check: Callable[[AsyncEngine | None], Awaitable[bool]] = database_is_ready,
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
    resolved_catalogue_client = catalogue_client
    if resolved_catalogue_client is None and resolved_settings.catalogue_service_url:
        service_token_provider = None
        if (
            resolved_settings.service_token_url
            and resolved_settings.service_client_id
            and resolved_settings.service_client_secret
        ):
            service_token_provider = KeycloakServiceTokenProvider(
                resolved_settings.service_token_url,
                resolved_settings.service_client_id,
                resolved_settings.service_client_secret,
                resolved_settings.catalogue_timeout_seconds,
            )
        resolved_catalogue_client = CatalogueHttpClient(
            resolved_settings.catalogue_service_url,
            resolved_settings.catalogue_timeout_seconds,
            service_token_provider=service_token_provider,
        )
    session_factory = create_session_factory(resolved_engine) if resolved_engine else None
    outbox_relay: Any | None = None
    if session_factory is not None and resolved_settings.kafka_bootstrap_servers:
        from app.application.outbox import KafkaEventPublisher, OutboxRelay

        outbox_relay = OutboxRelay(
            SqlAlchemyOrderOutboxStore(session_factory),
            KafkaEventPublisher(
                resolved_settings.kafka_bootstrap_servers,
                resolved_settings.kafka_client_id,
                resolved_settings.kafka_request_timeout_ms,
            ),
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("service_started", extra={"event": "service_started"})
        relay_task = asyncio.create_task(outbox_relay.run()) if outbox_relay else None
        yield
        if relay_task is not None:
            relay_task.cancel()
            try:
                await relay_task
            except asyncio.CancelledError:
                pass
        if outbox_relay is not None:
            await outbox_relay.close()
        if resolved_engine is not None:
            await resolved_engine.dispose()
        logger.info("service_stopped", extra={"event": "service_stopped"})

    application = FastAPI(
        title="ShopSphere Order Service",
        summary="Customer shopping carts and the Enterprise Order Processing boundary.",
        description=(
            "Keycloak-authenticated, customer-owned carts with catalogue-validated display "
            "snapshots and idempotent checkout using authoritative catalogue data and "
            "inventory reservations. Payment processing remains out of scope."
        ),
        version=resolved_settings.service_version,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database_engine = resolved_engine
    application.state.token_verifier = resolved_verifier
    application.state.catalogue_client = resolved_catalogue_client
    application.state.unit_of_work_factory = unit_of_work_factory or (
        (lambda: SqlAlchemyUnitOfWork(session_factory)) if session_factory is not None else None
    )
    application.state.readiness_check = readiness_check
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_v1_router)
    return application


app = create_app()
