"""Request-scoped correlation context."""

from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="unassigned")
