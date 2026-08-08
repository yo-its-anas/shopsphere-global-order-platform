"""Transport-only customer capability proxy; contains no customer domain logic."""

from __future__ import annotations

import logging
from time import perf_counter

import httpx2
from fastapi import Request
from starlette.responses import Response

from app.core.errors import GatewayError, UpstreamTimeoutError, UpstreamUnavailableError
from app.infrastructure.http_client import UpstreamHttpClient

logger = logging.getLogger(__name__)
_FORWARDED_REQUEST_HEADERS = frozenset({"authorization", "accept", "content-type"})
_FORWARDED_RESPONSE_HEADERS = frozenset({"content-type", "www-authenticate", "retry-after"})


class CustomerServiceProxy:
    """Forward fixed customer routes to the configured customer-service origin."""

    def __init__(self, client: UpstreamHttpClient) -> None:
        self._client = client

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
            logger.warning(
                "customer_service_timeout",
                extra={"event": "upstream_timeout", "upstream_service": "customer-service"},
            )
            raise UpstreamTimeoutError from exc
        except (httpx2.ConnectError, httpx2.NetworkError) as exc:
            logger.warning(
                "customer_service_unavailable",
                extra={
                    "event": "upstream_unavailable",
                    "upstream_service": "customer-service",
                },
            )
            raise UpstreamUnavailableError from exc
        except httpx2.HTTPError as exc:
            logger.warning(
                "customer_service_transport_error",
                extra={"event": "upstream_error", "upstream_service": "customer-service"},
            )
            raise GatewayError from exc

        logger.info(
            "customer_service_request_completed",
            extra={
                "event": "upstream_request_completed",
                "upstream_service": "customer-service",
                "upstream_status": upstream.status_code,
                "duration_ms": round((perf_counter() - started_at) * 1000, 3),
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

    async def is_ready(self, request_id: str) -> bool:
        try:
            response = await self._client.request(
                "GET", "/health/ready", headers={"X-Request-ID": request_id}
            )
            return response.status_code == 200
        except httpx2.HTTPError:
            logger.warning(
                "customer_service_readiness_unavailable",
                extra={
                    "event": "upstream_readiness_unavailable",
                    "upstream_service": "customer-service",
                },
            )
            return False
