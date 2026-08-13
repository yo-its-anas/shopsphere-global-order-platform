"""Shared test fixtures."""

import asyncio
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest

from app.core.config import Settings
from app.main import create_app


class StubUpstreamClient:
    """Captures bounded upstream calls without opening network connections."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.response = httpx2.Response(
            200,
            json={"forwarded": True},
            headers={"Content-Type": "application/json"},
        )
        self.error: httpx2.HTTPError | None = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Any = None,
        params: Any = None,
        content: bytes | None = None,
    ) -> httpx2.Response:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "headers": dict(headers or {}),
                "params": list(params or []),
                "content": content,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response

    async def aclose(self) -> None:
        return None


class ApiClient:
    """Synchronous facade over the in-process ASGI transport."""

    def __init__(self, application: object) -> None:
        self._application = application

    def request(self, method: str, url: str, **kwargs: Any) -> httpx2.Response:
        async def send() -> httpx2.Response:
            transport = httpx2.ASGITransport(app=self._application)
            async with httpx2.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as async_client:
                return await async_client.request(method, url, **kwargs)

        return asyncio.run(send())

    def get(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("GET", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("PATCH", url, **kwargs)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        service_name="api-gateway",
        service_version="0.1.0",
        environment="test",
        log_level="WARNING",
    )


@pytest.fixture
def upstream_client() -> StubUpstreamClient:
    return StubUpstreamClient()


@pytest.fixture
def catalogue_upstream_client() -> StubUpstreamClient:
    return StubUpstreamClient()


@pytest.fixture
def client(
    settings: Settings,
    upstream_client: StubUpstreamClient,
    catalogue_upstream_client: StubUpstreamClient,
) -> Iterator[ApiClient]:
    yield ApiClient(
        create_app(
            settings,
            customer_service_client=upstream_client,
            catalogue_service_client=catalogue_upstream_client,
        )
    )
