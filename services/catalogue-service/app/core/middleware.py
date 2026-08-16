"""Pure-ASGI correlation ID and structured request logging middleware."""

from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import correlation_id

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_REQUEST_ID_HEADER = b"x-request-id"
_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"})
logger = logging.getLogger(__name__)


def _route_template(scope: Scope) -> str:
    application = scope.get("app")
    patterns = getattr(getattr(application, "state", None), "metric_route_patterns", ())
    path = str(scope.get("path", ""))
    for template, pattern in patterns:
        if pattern.fullmatch(path):
            return str(template)
    return "unmatched"


class CorrelationIdMiddleware:
    """Attach a safe correlation ID to ASGI context, logs, and responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        supplied_request_id = ""
        for key, value in scope.get("headers", []):
            if key.lower() == _REQUEST_ID_HEADER:
                supplied_request_id = value.decode("latin-1")
                break
        request_id = (
            supplied_request_id
            if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else str(uuid4())
        )
        scope.setdefault("state", {})["correlation_id"] = request_id
        token = correlation_id.set(request_id)
        started_at = perf_counter()
        response_status = 500
        route = _route_template(scope)
        raw_method = str(scope.get("method", ""))
        method = raw_method if raw_method in _HTTP_METHODS else "OTHER"
        metrics = scope["app"].state.metrics
        metrics.request_started()

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != _REQUEST_ID_HEADER
                ]
                headers.append((_REQUEST_ID_HEADER, request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
            duration_seconds = perf_counter() - started_at
            metrics.observe_request(method, route, response_status, duration_seconds)
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "http_method": method,
                    "http_route": route,
                    "http_status": response_status,
                    "duration_ms": round(duration_seconds * 1000, 3),
                },
            )
        except Exception:
            duration_seconds = perf_counter() - started_at
            metrics.observe_request(method, route, 500, duration_seconds)
            logger.exception(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "http_method": method,
                    "http_route": route,
                    "duration_ms": round(duration_seconds * 1000, 3),
                },
            )
            raise
        finally:
            metrics.request_finished()
            correlation_id.reset(token)
