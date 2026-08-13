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
logger = logging.getLogger(__name__)


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
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "http_method": scope.get("method", ""),
                    "http_path": scope.get("path", ""),
                    "http_status": response_status,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                },
            )
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "http_method": scope.get("method", ""),
                    "http_path": scope.get("path", ""),
                    "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                },
            )
            raise
        finally:
            correlation_id.reset(token)
