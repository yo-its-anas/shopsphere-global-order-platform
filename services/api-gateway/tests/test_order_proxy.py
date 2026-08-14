"""Cart and Order gateway routing, propagation, and failure-policy tests."""

from __future__ import annotations

import logging
from typing import Any

import httpx2
import pytest

from app.core.config import Settings

ITEM_ID = "e87cccef-57d7-4cbd-a45f-4ea6f408eff3"
ORDER_ID = "27df75d1-46d3-4621-af91-a283b4280294"


@pytest.mark.parametrize(
    ("method", "external_path", "internal_path"),
    (
        ("GET", "/api/v1/carts/me", "/api/v1/carts/me"),
        ("POST", "/api/v1/carts/me/items", "/api/v1/carts/me/items"),
        ("DELETE", "/api/v1/carts/me/items", "/api/v1/carts/me/items"),
        ("PATCH", f"/api/v1/carts/me/items/{ITEM_ID}", f"/api/v1/carts/me/items/{ITEM_ID}"),
        (
            "DELETE",
            f"/api/v1/carts/me/items/{ITEM_ID}",
            f"/api/v1/carts/me/items/{ITEM_ID}",
        ),
        ("POST", "/api/v1/orders/checkout", "/api/v1/orders/checkout"),
        ("GET", "/api/v1/orders/me", "/api/v1/orders/me"),
        ("GET", f"/api/v1/orders/me/{ORDER_ID}", f"/api/v1/orders/me/{ORDER_ID}"),
        (
            "GET",
            f"/api/v1/orders/me/{ORDER_ID}/history",
            f"/api/v1/orders/me/{ORDER_ID}/history",
        ),
        (
            "GET",
            f"/api/v1/orders/me/{ORDER_ID}/audit",
            f"/api/v1/orders/me/{ORDER_ID}/audit",
        ),
        (
            "POST",
            f"/api/v1/orders/me/{ORDER_ID}/cancellation",
            f"/api/v1/orders/me/{ORDER_ID}/cancellation",
        ),
        ("GET", "/api/v1/orders/admin", "/api/v1/orders/admin"),
        (
            "GET",
            f"/api/v1/orders/admin/{ORDER_ID}",
            f"/api/v1/orders/admin/{ORDER_ID}",
        ),
        (
            "GET",
            f"/api/v1/orders/admin/{ORDER_ID}/history",
            f"/api/v1/orders/admin/{ORDER_ID}/history",
        ),
        (
            "GET",
            f"/api/v1/orders/admin/{ORDER_ID}/audit",
            f"/api/v1/orders/admin/{ORDER_ID}/audit",
        ),
        (
            "POST",
            f"/api/v1/orders/admin/{ORDER_ID}/status",
            f"/api/v1/orders/admin/{ORDER_ID}/status",
        ),
        (
            "POST",
            f"/api/v1/orders/admin/{ORDER_ID}/cancellation",
            f"/api/v1/orders/admin/{ORDER_ID}/cancellation",
        ),
    ),
)
def test_registered_order_routes_map_only_to_expected_internal_paths(
    client: Any,
    order_upstream_client: Any,
    method: str,
    external_path: str,
    internal_path: str,
) -> None:
    response = client.request(method, external_path)

    assert response.status_code == 200
    assert order_upstream_client.calls[0]["method"] == method
    assert order_upstream_client.calls[0]["path"] == internal_path


def test_cart_body_authentication_and_correlation_are_forwarded(
    client: Any, order_upstream_client: Any
) -> None:
    bearer = "signed.jwt.value"
    response = client.request(
        "POST",
        "/api/v1/carts/me/items",
        json={"product_id": "98e72695-c82f-4ad8-bf43-c6f00267a57b", "quantity": 2},
        headers={
            "Authorization": f"Bearer {bearer}",
            "X-Request-ID": "cart-correlation-19",
        },
    )

    assert response.status_code == 200
    call = order_upstream_client.calls[0]
    assert call["headers"]["authorization"] == f"Bearer {bearer}"
    assert call["headers"]["X-Request-ID"] == "cart-correlation-19"
    assert b'"quantity":2' in call["content"]
    assert response.headers["X-Request-ID"] == "cart-correlation-19"


def test_checkout_preserves_supplied_idempotency_key(
    client: Any, order_upstream_client: Any
) -> None:
    response = client.request(
        "POST",
        "/api/v1/orders/checkout",
        headers={"Idempotency-Key": "checkout-browser-retry-007"},
    )

    assert response.status_code == 200
    assert (
        order_upstream_client.calls[0]["headers"]["idempotency-key"] == "checkout-browser-retry-007"
    )


def test_checkout_does_not_invent_an_idempotency_key(
    client: Any, order_upstream_client: Any
) -> None:
    response = client.request("POST", "/api/v1/orders/checkout")

    assert response.status_code == 200
    assert "idempotency-key" not in order_upstream_client.calls[0]["headers"]


def test_order_history_query_is_forwarded_without_rewriting(
    client: Any, order_upstream_client: Any
) -> None:
    response = client.get(
        "/api/v1/orders/me",
        params=[("status", "CONFIRMED"), ("offset", "20"), ("limit", "10"), ("sort", "asc")],
    )

    assert response.status_code == 200
    assert order_upstream_client.calls[0]["params"] == [
        ("status", "CONFIRMED"),
        ("offset", "20"),
        ("limit", "10"),
        ("sort", "asc"),
    ]


@pytest.mark.parametrize("status_code", (401, 403, 409, 422))
def test_order_service_authentication_and_domain_responses_are_preserved(
    client: Any, order_upstream_client: Any, status_code: int
) -> None:
    order_upstream_client.response = httpx2.Response(
        status_code,
        json={"error": {"code": "downstream_policy", "message": "safe downstream response"}},
        headers={"Content-Type": "application/json"},
    )

    response = client.request("POST", "/api/v1/orders/checkout")

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == "downstream_policy"


def test_order_timeout_returns_standardized_safe_error(
    client: Any, order_upstream_client: Any
) -> None:
    order_upstream_client.error = httpx2.ReadTimeout(
        "internal timeout detail",
        request=httpx2.Request("POST", "http://order-service/api/v1/orders/checkout"),
    )

    response = client.request("POST", "/api/v1/orders/checkout")

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "upstream_timeout"
    assert "internal timeout detail" not in response.text


def test_unavailable_order_service_returns_standardized_safe_error(
    client: Any, order_upstream_client: Any
) -> None:
    order_upstream_client.error = httpx2.ConnectError(
        "connection refused at private origin",
        request=httpx2.Request("GET", "http://order-service/api/v1/orders/me"),
    )

    response = client.get("/api/v1/orders/me")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "upstream_unavailable"
    assert "private origin" not in response.text


def test_unregistered_order_route_is_not_forwarded(client: Any, order_upstream_client: Any) -> None:
    response = client.get(f"/api/v1/orders/me/{ORDER_ID}/arbitrary-proxy")

    assert response.status_code == 404
    assert order_upstream_client.calls == []


def test_request_cannot_override_order_upstream(client: Any, order_upstream_client: Any) -> None:
    response = client.get(
        "/api/v1/orders/me",
        headers={"X-Upstream-URL": "http://untrusted.example.test/private"},
    )

    assert response.status_code == 200
    assert order_upstream_client.calls[0]["path"] == "/api/v1/orders/me"
    assert "x-upstream-url" not in order_upstream_client.calls[0]["headers"]


def test_order_service_configuration_rejects_paths_and_credentials(monkeypatch: Any) -> None:
    monkeypatch.setenv("ORDER_SERVICE_URL", "http://user:credential@internal.test/private")

    with pytest.raises(ValueError, match=r"HTTP\(S\) origin"):
        Settings.from_environment()


def test_order_gateway_logs_never_include_sensitive_headers(
    client: Any,
    order_upstream_client: Any,
    caplog: Any,
) -> None:
    bearer = "order-sensitive-jwt-must-not-be-logged"
    idempotency_key = "sensitive-checkout-key-must-not-be-logged"
    order_upstream_client.error = httpx2.ReadTimeout(
        "timeout",
        request=httpx2.Request("POST", "http://order-service/api/v1/orders/checkout"),
    )

    with caplog.at_level(logging.WARNING):
        response = client.request(
            "POST",
            "/api/v1/orders/checkout",
            headers={
                "Authorization": f"Bearer {bearer}",
                "Idempotency-Key": idempotency_key,
                "Cookie": "private-session-value",
            },
        )

    assert response.status_code == 504
    assert bearer not in caplog.text
    assert idempotency_key not in caplog.text
    assert "private-session-value" not in caplog.text
    assert "cookie" not in order_upstream_client.calls[0]["headers"]


def test_readiness_reports_order_dependency(client: Any, order_upstream_client: Any) -> None:
    order_upstream_client.response = httpx2.Response(503, json={"status": "not_ready"})

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_openapi_describes_cart_checkout_and_order_paths(client: Any) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/carts/me" in paths
    assert "/api/v1/carts/me/items/{item_id}" in paths
    assert "/api/v1/orders/checkout" in paths
    assert "/api/v1/orders/me/{order_id}/history" in paths
    assert "/api/v1/orders/admin/{order_id}/status" in paths
    checkout_parameters = paths["/api/v1/orders/checkout"]["post"]["parameters"]
    assert any(
        parameter["in"] == "header" and parameter["name"] == "Idempotency-Key"
        for parameter in checkout_parameters
    )
