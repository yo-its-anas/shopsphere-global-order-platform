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
logger = logging.getLogger(__name__)


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

        try:
            response = await call_next(request)
            response.headers[_REQUEST_ID_HEADER] = request_id
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                },
            )
            return response
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                },
            )
            raise
        finally:
            correlation_id.reset(token)
