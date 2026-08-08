"""Asynchronous SQLAlchemy engine and session lifecycle."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_database_engine(database_url: str, connect_timeout_seconds: float = 3.0) -> AsyncEngine:
    """Create a pooled asynchronous engine without establishing an eager connection."""

    connect_args: dict[str, object] = {}
    if database_url.startswith("postgresql"):
        connect_args["connect_timeout"] = int(connect_timeout_seconds)
    return create_async_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create explicit asynchronous transaction-scoped sessions."""

    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def database_is_ready(engine: AsyncEngine | None) -> bool:
    """Execute a bounded connectivity query for readiness reporting."""

    if engine is None:
        return False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:  # readiness converts driver failures into a stable response
        return False


SessionFactory = Callable[[], AsyncSession]
