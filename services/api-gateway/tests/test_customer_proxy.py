"""Customer capability gateway transport and failure-policy tests."""

from __future__ import annotations

import logging
from typing import Any

import httpx2
import pytest

from app.core.config import Settings


def test_normal_customer_request_is_forwarded_to_fixed_internal_path(
    client: Any, upstream_client: Any
) -> None:
    upstream_client.response = httpx2.Response(
        200,
        json={"id": "customer-profile"},
        headers={"Content-Type": "application/json", "Server": "internal-detail"},
    )

    response = client.patch(
        "/api/v1/customers/me?locale=en",
        json={"first_name": "Amina"},
        headers={"Authorization": "Bearer opaque-test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": "customer-profile"}
    call = upstream_client.calls[0]
    assert call["method"] == "PATCH"
    assert call["path"] == "/api/v1/customers/me"
    assert call["params"] == [("locale", "en")]
    assert b'"first_name":"Amina"' in call["content"]
    assert "server" not in response.headers


def test_bearer_header_is_forwarded_without_modification(client: Any, upstream_client: Any) -> None:
    bearer_value = "signed.jwt.value"

    response = client.get(
        "/api/v1/customers/me/activity",
        headers={"Authorization": f"Bearer {bearer_value}"},
    )

    assert response.status_code == 200
    assert upstream_client.calls[0]["headers"]["authorization"] == f"Bearer {bearer_value}"


def test_timeout_returns_standardized_gateway_error(client: Any, upstream_client: Any) -> None:
    upstream_client.error = httpx2.ReadTimeout(
        "upstream timed out",
        request=httpx2.Request("GET", "http://customer-service/api/v1/customers/me"),
    )

    response = client.get("/api/v1/customers/me")

    assert response.status_code == 504
    assert response.json()["error"] == {
        "code": "upstream_timeout",
        "message": "The upstream service did not respond in time.",
    }
    assert response.json()["correlation_id"] == response.headers["X-Request-ID"]
    assert "customer-service" not in response.text


def test_unavailable_customer_service_returns_safe_error(client: Any, upstream_client: Any) -> None:
    upstream_client.error = httpx2.ConnectError(
        "connection refused",
        request=httpx2.Request("GET", "http://customer-service/api/v1/customers/me"),
    )

    response = client.get("/api/v1/customers/me")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "upstream_unavailable"
    assert "connection refused" not in response.text


def test_correlation_id_is_propagated_and_returned(client: Any, upstream_client: Any) -> None:
    response = client.get(
        "/api/v1/admin/customers/8e072573-653f-416d-a238-06e8230d42c4/activity",
        headers={"X-Request-ID": "gateway-correlation-42"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "gateway-correlation-42"
    assert upstream_client.calls[0]["headers"]["X-Request-ID"] == "gateway-correlation-42"


def test_invalid_route_is_not_forwarded(client: Any, upstream_client: Any) -> None:
    response = client.get("/api/v1/customers/me/not-configured")

    assert response.status_code == 404
    assert upstream_client.calls == []


def test_request_cannot_override_configured_upstream(client: Any, upstream_client: Any) -> None:
    response = client.get(
        "/api/v1/customers/me",
        headers={"X-Upstream-URL": "http://untrusted.example.test/private"},
    )

    assert response.status_code == 200
    assert upstream_client.calls[0]["path"] == "/api/v1/customers/me"
    assert "x-upstream-url" not in upstream_client.calls[0]["headers"]


def test_customer_service_configuration_rejects_paths_and_credentials(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv(
        "CUSTOMER_SERVICE_URL", "http://user:credential@internal.example.test/private"
    )

    with pytest.raises(ValueError, match=r"HTTP\(S\) origin"):
        Settings.from_environment()


def test_gateway_logs_never_include_bearer_token(
    client: Any,
    upstream_client: Any,
    caplog: Any,
) -> None:
    bearer_value = "sensitive-jwt-must-not-be-logged"
    upstream_client.error = httpx2.ReadTimeout(
        "timeout",
        request=httpx2.Request("GET", "http://customer-service/api/v1/customers/me"),
    )

    with caplog.at_level(logging.WARNING):
        response = client.get(
            "/api/v1/customers/me",
            headers={"Authorization": f"Bearer {bearer_value}"},
        )

    assert response.status_code == 504
    assert bearer_value not in caplog.text
    assert all(bearer_value not in record.getMessage() for record in caplog.records)


def test_readiness_reports_customer_service_dependency(client: Any, upstream_client: Any) -> None:
    upstream_client.response = httpx2.Response(503, json={"status": "not_ready"})

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "api-gateway",
        "version": "0.1.0",
    }


def test_openapi_describes_customer_capability_paths(client: Any) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/customers/me" in paths
    assert "/api/v1/customers/me/addresses/{address_id}" in paths
    assert "/api/v1/customers/me/activity" in paths
    assert "/api/v1/admin/customers/{customer_id}/activity" in paths
