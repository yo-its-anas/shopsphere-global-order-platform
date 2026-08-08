"""Bounded HTTP client used only for configured internal services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import httpx2


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

    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._client = httpx2.AsyncClient(
            base_url=base_url,
            timeout=httpx2.Timeout(timeout_seconds),
            follow_redirects=False,
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
        return await self._client.request(
            method,
            path,
            headers=headers,
            params=params,
            content=content,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
