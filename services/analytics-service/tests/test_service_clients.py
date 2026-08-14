"""Owner-API parsing and calculation tests for fixed analytics clients."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx2
import pytest

from app.core.config import Settings
from app.infrastructure.service_clients import (
    HttpDashboardSources,
    InvalidSourceResponseError,
    ReadOnlyServiceClient,
)


def _settings() -> Settings:
    return Settings("analytics-service", "0.1.0", "test", "WARNING")


def _response(payload: dict, status: int = 200) -> httpx2.Response:
    return httpx2.Response(
        status, content=json.dumps(payload), headers={"Content-Type": "application/json"}
    )


@pytest.mark.anyio
async def test_order_calculation_excludes_cancelled_revenue_and_calculates_fulfilment() -> None:
    now = datetime(2026, 8, 14, tzinfo=timezone.utc).isoformat()
    items = [
        ("CONFIRMED", "100.0000"),
        ("PROCESSING", "50.0000"),
        ("FULFILLED", "25.5000"),
        ("CANCELLED", "999.0000"),
    ]

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/api/v1/orders/admin"
        assert request.headers["Authorization"] == "Bearer safe-token"
        return _response(
            {
                "items": [
                    {
                        "order_id": f"00000000-0000-4000-8000-00000000000{index}",
                        "order_number": f"SS-TEST-{index}",
                        "status": status,
                        "currency_code": "USD",
                        "total": total,
                        "created_at": now,
                        "updated_at": now,
                    }
                    for index, (status, total) in enumerate(items, start=1)
                ],
                "offset": 0,
                "limit": 100,
                "total": 4,
            }
        )

    client = ReadOnlyServiceClient(
        "http://order-service:8000", 1, transport=httpx2.MockTransport(handler)
    )
    sources = HttpDashboardSources(_settings(), order_client=client)
    try:
        result = await sources.orders("safe-token", "correlation")
    finally:
        await sources.aclose()

    assert result.total_orders == 4
    assert result.simulated_revenue_by_currency == {"USD": result.total_revenue_simulated}
    assert str(result.total_revenue_simulated) == "175.5000"
    assert result.cancelled_orders == 1
    assert str(result.fulfilment_rate) == "33.33"


@pytest.mark.anyio
async def test_customer_registration_count_uses_all_existing_api_pages() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        offset = int(request.url.params["offset"])
        count = 100 if offset == 0 else 2
        return _response({"items": [{} for _ in range(count)], "offset": offset, "limit": 100})

    client = ReadOnlyServiceClient(
        "http://customer-service:8000", 1, transport=httpx2.MockTransport(handler)
    )
    sources = HttpDashboardSources(_settings(), customer_client=client)
    try:
        result = await sources.customers("safe-token", "correlation")
    finally:
        await sources.aclose()

    assert result.customer_count == 102


@pytest.mark.anyio
async def test_inventory_counts_are_accepted_only_when_invariants_hold() -> None:
    now = datetime(2026, 8, 14, tzinfo=timezone.utc).isoformat()

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v1/products":
            return _response({"items": [], "offset": 0, "limit": 1, "total": 15})
        return _response(
            {
                "location_code": "PRIMARY",
                "total_products_tracked": 10,
                "in_stock_products": 5,
                "low_stock_products": 3,
                "out_of_stock_products": 2,
                "total_units_on_hand": 80,
                "reserved_units": 10,
                "available_units": 70,
                "calculated_at": now,
            }
        )

    client = ReadOnlyServiceClient(
        "http://catalogue-service:8000", 1, transport=httpx2.MockTransport(handler)
    )
    sources = HttpDashboardSources(_settings(), catalogue_client=client)
    try:
        result = await sources.inventory("safe-token", "correlation")
    finally:
        await sources.aclose()

    assert result.product_count == 15
    assert result.available_product_count == 8
    assert result.out_of_stock_count == 2


@pytest.mark.anyio
async def test_invalid_inventory_response_is_rejected() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v1/products":
            return _response({"items": [], "offset": 0, "limit": 1, "total": 1})
        return _response({"unexpected": "shape"})

    client = ReadOnlyServiceClient(
        "http://catalogue-service:8000", 1, transport=httpx2.MockTransport(handler)
    )
    sources = HttpDashboardSources(_settings(), catalogue_client=client)
    try:
        with pytest.raises(InvalidSourceResponseError):
            await sources.inventory("safe-token", "correlation")
    finally:
        await sources.aclose()
