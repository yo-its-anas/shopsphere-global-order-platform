"""Transport-only analytics capability proxy; contains no domain behavior."""

from __future__ import annotations

import logging
from time import perf_counter

import httpx2
from fastapi import Request
from starlette.responses import Response

from app.core.errors import GatewayError, UpstreamTimeoutError, UpstreamUnavailableError
from app.core.metrics import ServiceMetrics
from app.infrastructure.http_client import UpstreamHttpClient

logger = logging.getLogger(__name__)
_FORWARDED_REQUEST_HEADERS = frozenset({"authorization", "accept", "content-type"})
_FORWARDED_RESPONSE_HEADERS = frozenset({"content-type", "retry-after"})


class AnalyticsServiceProxy:
    """Forward only explicitly registered routes to the configured analytics origin."""

    def __init__(self, client: UpstreamHttpClient, metrics: ServiceMetrics) -> None:
        self._client = client
        self._metrics = metrics

    async def forward(self, request: Request, upstream_path: str) -> Response:
        request_id = str(request.state.correlation_id)
        headers = {
            name: value
            for name, value in request.headers.items()
            if name.casefold() in _FORWARDED_REQUEST_HEADERS
        }
        headers["X-Request-ID"] = request_id
        started_at = perf_counter()
        try:
            upstream = await self._client.request(
                request.method,
                upstream_path,
                headers=headers,
                params=list(request.query_params.multi_items()),
                content=await request.body(),
            )
        except httpx2.TimeoutException as exc:
            self._metrics.observe_upstream(
                "analytics-service", "timeout", None, perf_counter() - started_at
            )
            logger.warning(
                "analytics_service_timeout",
                extra={"event": "upstream_timeout", "upstream_service": "analytics-service"},
            )
            raise UpstreamTimeoutError from exc
        except (httpx2.ConnectError, httpx2.NetworkError) as exc:
            self._metrics.observe_upstream(
                "analytics-service", "unavailable", None, perf_counter() - started_at
            )
            logger.warning(
                "analytics_service_unavailable",
                extra={"event": "upstream_unavailable", "upstream_service": "analytics-service"},
            )
            raise UpstreamUnavailableError from exc
        except httpx2.HTTPError as exc:
            self._metrics.observe_upstream(
                "analytics-service", "transport_error", None, perf_counter() - started_at
            )
            logger.warning(
                "analytics_service_transport_error",
                extra={"event": "upstream_error", "upstream_service": "analytics-service"},
            )
            raise GatewayError from exc

        duration_seconds = perf_counter() - started_at
        result = "success" if upstream.status_code < 400 else "http_error"
        self._metrics.observe_upstream(
            "analytics-service", result, upstream.status_code, duration_seconds
        )
        logger.info(
            "analytics_service_request_completed",
            extra={
                "event": "upstream_request_completed",
                "upstream_service": "analytics-service",
                "upstream_status": upstream.status_code,
                "duration_ms": round(duration_seconds * 1000, 3),
            },
        )
        response_headers = {
            name: value
            for name, value in upstream.headers.items()
            if name.casefold() in _FORWARDED_RESPONSE_HEADERS
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
        )
