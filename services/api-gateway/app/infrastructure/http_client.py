"""Bounded HTTP client used only for configured internal services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import httpx2

from app.core.telemetry import Telemetry


class UpstreamHttpClient(Protocol):
    """Minimal client boundary supporting deterministic gateway tests."""

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: list[tuple[str, str]] | None = None,
        content: bytes | None = None,
    ) -> httpx2.Response: ...

    async def aclose(self) -> None: ...


class ConfiguredHttpClient:
    """HTTP client whose origin is fixed during application construction."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        telemetry: Telemetry,
        upstream_service: str,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._telemetry = telemetry
        self._upstream_service = upstream_service
        self._client = httpx2.AsyncClient(
            base_url=base_url,
            timeout=httpx2.Timeout(timeout_seconds),
            follow_redirects=False,
            transport=transport,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: list[tuple[str, str]] | None = None,
        content: bytes | None = None,
    ) -> httpx2.Response:
        propagated_headers = dict(headers or {})
        with self._telemetry.client_span(
            f"{self._upstream_service} {method.upper()}",
            upstream_service=self._upstream_service,
            method=method,
        ) as span:
            self._telemetry.inject(propagated_headers)
            response = await self._client.request(
                method,
                path,
                headers=propagated_headers,
                params=params,
                content=content,
            )
            self._telemetry.set_http_status(span, response.status_code)
            return response

    async def aclose(self) -> None:
        await self._client.aclose()
