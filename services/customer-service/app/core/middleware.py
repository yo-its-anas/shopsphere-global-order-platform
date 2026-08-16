"""Correlation ID and structured request logging middleware."""

from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import correlation_id

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_REQUEST_ID_HEADER = "X-Request-ID"
_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"})
logger = logging.getLogger(__name__)


def _route_template(request: Request) -> str:
    for template, pattern in request.app.state.metric_route_patterns:
        if pattern.fullmatch(request.url.path):
            return str(template)
    return "unmatched"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a safe correlation ID to request context, logs, and responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied_request_id = request.headers.get(_REQUEST_ID_HEADER, "")
        request_id = (
            supplied_request_id
            if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else str(uuid4())
        )
        request.state.correlation_id = request_id
        token = correlation_id.set(request_id)
        started_at = perf_counter()
        route = _route_template(request)
        method = request.method if request.method in _HTTP_METHODS else "OTHER"
        request.app.state.metrics.request_started()

        try:
            response = await call_next(request)
            response.headers[_REQUEST_ID_HEADER] = request_id
            duration_seconds = perf_counter() - started_at
            request.app.state.metrics.observe_request(
                method, route, response.status_code, duration_seconds
            )
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "http_method": method,
                    "http_route": route,
                    "http_status": response.status_code,
                    "duration_ms": round(duration_seconds * 1000, 3),
                },
            )
            return response
        except Exception:
            duration_seconds = perf_counter() - started_at
            request.app.state.metrics.observe_request(method, route, 500, duration_seconds)
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
            request.app.state.metrics.request_finished()
            correlation_id.reset(token)
