"""Deterministic authentication and source doubles for dashboard API tests."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from app.core.errors import AuthenticationError
from app.core.security import Principal
from app.domain.models import (
    CustomerKpis,
    DependencyState,
    InventoryKpis,
    OrderKpis,
    SourceResult,
)


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    content: bytes
    headers: dict[str, str]

    @property
    def text(self) -> str:
        return self.content.decode()

    def json(self) -> Any:
        return json.loads(self.content)


class ApiHeaders(dict[str, str]):
    def __getitem__(self, key: str) -> str:
        return super().__getitem__(key.casefold())


class ApiClient:
    """Deterministic ASGI client matching established service test conventions."""

    def __init__(self, application: Any) -> None:
        self._application = application
        self._loop = asyncio.new_event_loop()

    def close(self) -> None:
        self._loop.close()

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> ApiResponse:
        parsed = urlsplit(url)
        request_headers = [
            (key.casefold().encode("latin-1"), value.encode("latin-1"))
            for key, value in (headers or {}).items()
        ]

        async def send_request() -> ApiResponse:
            request_sent = False
            response_complete = asyncio.Event()
            response_status = 500
            response_headers = ApiHeaders()
            response_parts: list[bytes] = []

            async def receive() -> dict[str, object]:
                nonlocal request_sent
                if not request_sent:
                    request_sent = True
                    return {"type": "http.request", "body": b"", "more_body": False}
                await response_complete.wait()
                return {"type": "http.disconnect"}

            async def send(message: dict[str, Any]) -> None:
                nonlocal response_status
                if message["type"] == "http.response.start":
                    response_status = int(message["status"])
                    response_headers.update(
                        {
                            key.decode("latin-1").casefold(): value.decode("latin-1")
                            for key, value in message.get("headers", [])
                        }
                    )
                elif message["type"] == "http.response.body":
                    response_parts.append(message.get("body", b""))
                    if not message.get("more_body", False):
                        response_complete.set()

            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": parsed.path,
                "raw_path": parsed.path.encode(),
                "query_string": parsed.query.encode(),
                "root_path": "",
                "headers": request_headers,
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
                "state": {},
            }
            await self._application(scope, receive, send)
            return ApiResponse(response_status, b"".join(response_parts), response_headers)

        return self._loop.run_until_complete(send_request())


class FakeTokenVerifier:
    async def verify(self, token: str) -> Principal:
        roles_by_token = {
            "operations-token": frozenset({"operations_admin"}),
            "support-token": frozenset({"support"}),
            "customer-token": frozenset({"customer"}),
        }
        roles = roles_by_token.get(token)
        if roles is None:
            raise AuthenticationError
        return Principal(
            subject=f"subject-{token}",
            username=None,
            email=None,
            roles=roles,
        )


class FakeSources:
    def __init__(self) -> None:
        self.customer_value = CustomerKpis(customer_count=8)
        self.inventory_value = InventoryKpis(
            product_count=12,
            total_products_tracked=10,
            in_stock_count=6,
            low_stock_count=3,
            out_of_stock_count=1,
            total_units_on_hand=120,
            reserved_units=20,
            available_units=100,
            calculated_at=datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc),
        )
        self.order_value = OrderKpis(
            total_orders=10,
            simulated_revenue_by_currency={"USD": Decimal("750.0000")},
            confirmed_orders=3,
            processing_orders=2,
            fulfilled_orders=3,
            cancelled_orders=2,
            failed_orders=0,
            fulfilment_rate=Decimal("37.50"),
        )
        self.customer_error: Exception | None = None
        self.inventory_error: Exception | None = None
        self.order_error: Exception | None = None
        self.health_values = [
            SourceResult("customer-service", True, DependencyState.AVAILABLE),
            SourceResult("catalogue-service", True, DependencyState.AVAILABLE),
            SourceResult("order-service", True, DependencyState.AVAILABLE),
        ]
        self.closed = False
        self.tokens: list[str] = []

    async def customers(self, access_token: str, correlation_id: str) -> CustomerKpis:
        self.tokens.append(access_token)
        if self.customer_error:
            raise self.customer_error
        return self.customer_value

    async def inventory(self, access_token: str, correlation_id: str) -> InventoryKpis:
        self.tokens.append(access_token)
        if self.inventory_error:
            raise self.inventory_error
        return self.inventory_value

    async def orders(self, access_token: str, correlation_id: str) -> OrderKpis:
        self.tokens.append(access_token)
        if self.order_error:
            raise self.order_error
        return self.order_value

    async def health(self, correlation_id: str) -> list[SourceResult]:
        return self.health_values

    async def aclose(self) -> None:
        self.closed = True
