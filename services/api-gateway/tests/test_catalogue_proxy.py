"""Catalogue and Inventory gateway routing and failure-policy tests."""

from __future__ import annotations

import logging
from typing import Any

import httpx2
import pytest

from app.core.config import Settings

PRODUCT_ID = "410fe795-4c5a-4331-be47-ceee8b8b7d1f"
CATEGORY_ID = "1390f242-00ed-474b-a3b1-617f3b7e2b72"


@pytest.mark.parametrize(
    ("method", "external_path", "internal_path"),
    (
        ("GET", "/api/v1/categories", "/api/v1/categories"),
        ("POST", "/api/v1/categories", "/api/v1/categories"),
        ("GET", f"/api/v1/categories/{CATEGORY_ID}", f"/api/v1/categories/{CATEGORY_ID}"),
        ("PATCH", f"/api/v1/categories/{CATEGORY_ID}", f"/api/v1/categories/{CATEGORY_ID}"),
        ("GET", "/api/v1/products", "/api/v1/products"),
        ("POST", "/api/v1/products", "/api/v1/products"),
        ("GET", f"/api/v1/products/{PRODUCT_ID}", f"/api/v1/products/{PRODUCT_ID}"),
        ("PATCH", f"/api/v1/products/{PRODUCT_ID}", f"/api/v1/products/{PRODUCT_ID}"),
        (
            "POST",
            f"/api/v1/products/{PRODUCT_ID}/deactivate",
            f"/api/v1/products/{PRODUCT_ID}/deactivate",
        ),
        (
            "GET",
            f"/api/v1/products/{PRODUCT_ID}/prices",
            f"/api/v1/products/{PRODUCT_ID}/prices",
        ),
        (
            "PUT",
            f"/api/v1/products/{PRODUCT_ID}/prices/USD",
            f"/api/v1/products/{PRODUCT_ID}/prices/USD",
        ),
        ("GET", "/api/v1/inventory", "/api/v1/inventory"),
        ("GET", "/api/v1/inventory/statistics", "/api/v1/inventory/statistics"),
        (
            "GET",
            f"/api/v1/inventory/products/{PRODUCT_ID}",
            f"/api/v1/inventory/products/{PRODUCT_ID}",
        ),
        (
            "GET",
            f"/api/v1/inventory/products/{PRODUCT_ID}/availability",
            f"/api/v1/inventory/products/{PRODUCT_ID}/availability",
        ),
        (
            "POST",
            f"/api/v1/inventory/products/{PRODUCT_ID}/initialize",
            f"/api/v1/inventory/products/{PRODUCT_ID}/initialize",
        ),
        (
            "POST",
            f"/api/v1/inventory/products/{PRODUCT_ID}/adjustments",
            f"/api/v1/inventory/products/{PRODUCT_ID}/adjustments",
        ),
        (
            "PATCH",
            f"/api/v1/inventory/products/{PRODUCT_ID}/settings",
            f"/api/v1/inventory/products/{PRODUCT_ID}/settings",
        ),
        (
            "GET",
            f"/api/v1/inventory/products/{PRODUCT_ID}/movements",
            f"/api/v1/inventory/products/{PRODUCT_ID}/movements",
        ),
    ),
)
def test_registered_catalogue_route_table_maps_only_to_expected_internal_paths(
    client: Any,
    catalogue_upstream_client: Any,
    method: str,
    external_path: str,
    internal_path: str,
) -> None:
    response = client.request(method, external_path)

    assert response.status_code == 200
    assert catalogue_upstream_client.calls[0]["method"] == method
    assert catalogue_upstream_client.calls[0]["path"] == internal_path


def test_catalogue_request_is_forwarded_to_fixed_internal_path(
    client: Any, catalogue_upstream_client: Any
) -> None:
    catalogue_upstream_client.response = httpx2.Response(
        200,
        json={"id": PRODUCT_ID, "sku": "SAFE-001"},
        headers={"Content-Type": "application/json", "Server": "internal-detail"},
    )

    response = client.get(
        f"/api/v1/products/{PRODUCT_ID}",
        headers={"Authorization": "Bearer opaque-test-token"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == PRODUCT_ID
    call = catalogue_upstream_client.calls[0]
    assert call["method"] == "GET"
    assert call["path"] == f"/api/v1/products/{PRODUCT_ID}"
    assert "server" not in response.headers


def test_search_and_pagination_query_values_are_forwarded_without_rewriting(
    client: Any, catalogue_upstream_client: Any
) -> None:
    response = client.get(
        "/api/v1/products",
        params=[
            ("query", "steel bottle"),
            ("category_id", CATEGORY_ID),
            ("offset", "20"),
            ("limit", "10"),
            ("sort_by", "name"),
            ("sort_direction", "desc"),
        ],
    )

    assert response.status_code == 200
    assert catalogue_upstream_client.calls[0]["params"] == [
        ("query", "steel bottle"),
        ("category_id", CATEGORY_ID),
        ("offset", "20"),
        ("limit", "10"),
        ("sort_by", "name"),
        ("sort_direction", "desc"),
    ]


def test_inventory_and_pricing_mutations_forward_method_body_and_authentication(
    client: Any, catalogue_upstream_client: Any
) -> None:
    bearer = "signed.jwt.value"
    price = client.request(
        "PUT",
        f"/api/v1/products/{PRODUCT_ID}/prices/USD",
        json={"amount": "19.9900"},
        headers={"Authorization": f"Bearer {bearer}"},
    )
    adjustment = client.request(
        "POST",
        f"/api/v1/inventory/products/{PRODUCT_ID}/adjustments",
        json={
            "movement_type": "STOCK_RECEIPT",
            "quantity_delta": 5,
            "reason": "Test receipt",
            "idempotency_key": "gateway-receipt-001",
        },
        headers={"Authorization": f"Bearer {bearer}"},
    )

    assert price.status_code == adjustment.status_code == 200
    assert catalogue_upstream_client.calls[0]["method"] == "PUT"
    assert catalogue_upstream_client.calls[0]["headers"]["authorization"] == f"Bearer {bearer}"
    assert b'"amount":"19.9900"' in catalogue_upstream_client.calls[0]["content"]
    assert catalogue_upstream_client.calls[1]["method"] == "POST"
    assert catalogue_upstream_client.calls[1]["headers"]["authorization"] == f"Bearer {bearer}"


def test_correlation_id_is_propagated_to_catalogue_service(
    client: Any, catalogue_upstream_client: Any
) -> None:
    response = client.get(
        "/api/v1/inventory/statistics",
        headers={"X-Request-ID": "catalogue-gateway-correlation"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "catalogue-gateway-correlation"
    assert (
        catalogue_upstream_client.calls[0]["headers"]["X-Request-ID"]
        == "catalogue-gateway-correlation"
    )


def test_catalogue_timeout_returns_standardized_safe_error(
    client: Any, catalogue_upstream_client: Any
) -> None:
    catalogue_upstream_client.error = httpx2.ReadTimeout(
        "upstream timed out at internal address",
        request=httpx2.Request("GET", "http://catalogue-service/api/v1/products"),
    )

    response = client.get("/api/v1/products")

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "upstream_timeout"
    assert response.json()["correlation_id"] == response.headers["X-Request-ID"]
    assert "catalogue-service" not in response.text
    assert "internal address" not in response.text


def test_unavailable_catalogue_service_returns_standardized_safe_error(
    client: Any, catalogue_upstream_client: Any
) -> None:
    catalogue_upstream_client.error = httpx2.ConnectError(
        "connection refused",
        request=httpx2.Request("GET", "http://catalogue-service/api/v1/categories"),
    )

    response = client.get("/api/v1/categories")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "upstream_unavailable",
        "message": "The requested capability is temporarily unavailable.",
    }
    assert "connection refused" not in response.text


def test_other_catalogue_transport_failure_returns_safe_bad_gateway(
    client: Any, catalogue_upstream_client: Any
) -> None:
    catalogue_upstream_client.error = httpx2.ProtocolError(
        "malformed internal response detail",
        request=httpx2.Request("GET", "http://catalogue-service/api/v1/products"),
    )

    response = client.get("/api/v1/products")

    assert response.status_code == 502
    assert response.json()["error"] == {
        "code": "upstream_error",
        "message": "The upstream service could not complete the request.",
    }
    assert "malformed internal response" not in response.text


def test_invalid_catalogue_route_is_not_forwarded(
    client: Any, catalogue_upstream_client: Any
) -> None:
    response = client.get(f"/api/v1/products/{PRODUCT_ID}/arbitrary-proxy")

    assert response.status_code == 404
    assert catalogue_upstream_client.calls == []


def test_request_cannot_override_catalogue_upstream(
    client: Any, catalogue_upstream_client: Any
) -> None:
    response = client.get(
        "/api/v1/products",
        headers={"X-Upstream-URL": "http://untrusted.example.test/private"},
    )

    assert response.status_code == 200
    assert catalogue_upstream_client.calls[0]["path"] == "/api/v1/products"
    assert "x-upstream-url" not in catalogue_upstream_client.calls[0]["headers"]


def test_catalogue_service_configuration_rejects_paths_and_credentials(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv(
        "CATALOGUE_SERVICE_URL", "http://user:credential@internal.example.test/private"
    )

    with pytest.raises(ValueError, match=r"HTTP\(S\) origin"):
        Settings.from_environment()


def test_catalogue_gateway_logs_never_include_bearer_token(
    client: Any,
    catalogue_upstream_client: Any,
    caplog: Any,
) -> None:
    bearer = "catalogue-sensitive-jwt-must-not-be-logged"
    catalogue_upstream_client.error = httpx2.ReadTimeout(
        "timeout",
        request=httpx2.Request("GET", "http://catalogue-service/api/v1/products"),
    )

    with caplog.at_level(logging.WARNING):
        response = client.get("/api/v1/products", headers={"Authorization": f"Bearer {bearer}"})

    assert response.status_code == 504
    assert bearer not in caplog.text
    assert all(bearer not in record.getMessage() for record in caplog.records)


def test_readiness_reports_catalogue_dependency(
    client: Any, catalogue_upstream_client: Any
) -> None:
    catalogue_upstream_client.response = httpx2.Response(503, json={"status": "not_ready"})

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "api-gateway",
        "version": "0.1.0",
    }


def test_openapi_describes_catalogue_and_inventory_paths(client: Any) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/categories/{category_id}" in paths
    assert "/api/v1/products" in paths
    assert "/api/v1/products/{product_id}/prices/{currency_code}" in paths
    assert "/api/v1/inventory/products/{product_id}/availability" in paths
    assert "/api/v1/inventory/products/{product_id}/adjustments" in paths
    assert "/api/v1/inventory/statistics" in paths
