"""Fixed-origin catalogue client contract tests."""

import asyncio
from uuid import uuid4

import httpx2
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.core.errors import DependencyUnavailableError
from app.core.telemetry import Telemetry
from app.infrastructure.catalogue_client import CatalogueHttpClient


def test_catalogue_client_preserves_api_prefix_and_safe_headers() -> None:
    product_id = uuid4()
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if request.url.path.endswith("/prices"):
            return httpx2.Response(
                200,
                json={
                    "items": [
                        {
                            "amount": "24.9900",
                            "currency_code": "USD",
                            "is_active": True,
                        }
                    ]
                },
            )
        if request.url.path.endswith("/availability"):
            return httpx2.Response(200, json={"quantity_available": 7})
        return httpx2.Response(
            200,
            json={
                "id": str(product_id),
                "sku": "TEST-SKU",
                "name": "Synthetic Product",
                "status": "active",
                "is_searchable": True,
            },
        )

    client = CatalogueHttpClient(
        "http://catalogue.test/api/v1",
        1.0,
        transport=httpx2.MockTransport(handler),
    )
    snapshot = asyncio.run(
        client.get_product_snapshot(product_id, "USD", "synthetic-token", "catalogue-client-test")
    )

    assert [request.url.path for request in requests] == [
        f"/api/v1/products/{product_id}",
        f"/api/v1/products/{product_id}/prices",
        f"/api/v1/inventory/products/{product_id}/availability",
    ]
    assert all(request.headers["x-request-id"] == "catalogue-client-test" for request in requests)
    assert all(request.headers["authorization"] == "Bearer synthetic-token" for request in requests)
    assert snapshot.unit_price.as_tuple().exponent == -4
    assert snapshot.quantity_available == 7


def test_catalogue_client_maps_network_failure_to_dependency_error() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("synthetic connection failure")

    client = CatalogueHttpClient(
        "http://catalogue.test/api/v1",
        1.0,
        transport=httpx2.MockTransport(handler),
    )

    with pytest.raises(DependencyUnavailableError):
        asyncio.run(
            client.get_product_snapshot(uuid4(), "USD", "synthetic-token", "catalogue-client-test")
        )


def test_catalogue_client_propagates_trace_context_without_recording_token() -> None:
    product_id = uuid4()
    requests: list[httpx2.Request] = []
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    telemetry = Telemetry(provider, "order-service")

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if request.url.path.endswith("/prices"):
            return httpx2.Response(
                200,
                json={"items": [{"amount": "10.0000", "currency_code": "USD", "is_active": True}]},
            )
        if request.url.path.endswith("/availability"):
            return httpx2.Response(200, json={"quantity_available": 1})
        return httpx2.Response(
            200,
            json={
                "id": str(product_id),
                "sku": "TRACE-SKU",
                "name": "Trace Product",
                "status": "active",
                "is_searchable": True,
            },
        )

    client = CatalogueHttpClient(
        "http://catalogue.test/api/v1",
        1.0,
        transport=httpx2.MockTransport(handler),
        telemetry=telemetry,
    )

    async def invoke() -> None:
        with telemetry.tracer.start_as_current_span("order.checkout"):
            await client.get_product_snapshot(
                product_id, "USD", "synthetic-secret-token", "safe-correlation"
            )

    asyncio.run(invoke())

    assert all("traceparent" in request.headers for request in requests)
    assert "synthetic-secret-token" not in repr(exporter.get_finished_spans())
