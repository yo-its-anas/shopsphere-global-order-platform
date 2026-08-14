"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.routing import compile_path

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.v1.router import api_v1_router
from app.application.cache import CacheBackend, CacheKeys, InstrumentedCache, NullCache
from app.application.catalogue import UnitOfWorkFactory
from app.application.outbox import KafkaEventPublisher, OutboxRelay
from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics import ServiceMetrics
from app.core.middleware import CorrelationIdMiddleware
from app.core.security import KeycloakTokenVerifier, TokenVerifier
from app.infrastructure.cache import RedisJsonCache
from app.infrastructure.database import (
    create_database_engine,
    create_session_factory,
    database_is_ready,
)
from app.infrastructure.repositories import SqlAlchemyOutboxStore, SqlAlchemyUnitOfWork

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
    {
        "name": "Internal inventory reservations",
        "description": (
            "Service/admin-authorized reservation lifecycle commands kept outside "
            "the public API Gateway allow-list."
        ),
    },
]


def create_app(
    settings: Settings | None = None,
    *,
    database_engine: AsyncEngine | None = None,
    token_verifier: TokenVerifier | None = None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
    cache_backend: CacheBackend | None = None,
    database_readiness_checker: DatabaseReadinessChecker = database_is_ready,
) -> FastAPI:
    """Create an independently configurable FastAPI application."""

    resolved_settings = settings or Settings.from_environment()
    configure_logging(resolved_settings.log_level)
    metrics = ServiceMetrics(
        resolved_settings.service_name,
        resolved_settings.service_version,
        resolved_settings.environment,
    )
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
    outbox_relay: OutboxRelay | None = None
    resolved_cache = cache_backend
    if resolved_cache is None and resolved_settings.redis_url and resolved_settings.redis_password:
        resolved_cache = RedisJsonCache(
            resolved_settings.redis_url,
            resolved_settings.redis_password,
            resolved_settings.redis_connect_timeout_seconds,
        )
    if resolved_cache is None:
        resolved_cache = NullCache()
    resolved_cache = InstrumentedCache(resolved_cache, metrics)
    if resolved_unit_of_work_factory is None and resolved_engine is not None:
        resolved_session_factory = create_session_factory(resolved_engine)

        def build_unit_of_work() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(resolved_session_factory)

        resolved_unit_of_work_factory = build_unit_of_work
        if resolved_settings.kafka_bootstrap_servers:
            outbox_relay = OutboxRelay(
                SqlAlchemyOutboxStore(resolved_session_factory),
                KafkaEventPublisher(
                    resolved_settings.kafka_bootstrap_servers,
                    resolved_settings.kafka_client_id,
                    resolved_settings.kafka_request_timeout_ms,
                ),
                batch_size=resolved_settings.outbox_batch_size,
                poll_interval_seconds=resolved_settings.outbox_poll_interval_seconds,
                retry_base_seconds=resolved_settings.outbox_retry_base_seconds,
                lease_seconds=resolved_settings.outbox_lease_seconds,
                metrics=metrics,
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
        await resolved_cache.close()
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
    application.state.metrics = metrics
    application.state.database_engine = resolved_engine
    application.state.database_readiness_checker = database_readiness_checker
    application.state.token_verifier = resolved_verifier
    application.state.unit_of_work_factory = resolved_unit_of_work_factory
    application.state.cache = resolved_cache
    application.state.cache_keys = CacheKeys(
        resolved_settings.cache_key_prefix, resolved_settings.environment
    )
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(metrics_router)
    application.include_router(api_v1_router)
    metric_paths = ("/metrics", *application.openapi()["paths"])
    application.state.metric_route_patterns = tuple(
        (path, compile_path(path)[0]) for path in metric_paths
    )
    return application


app = create_app()
