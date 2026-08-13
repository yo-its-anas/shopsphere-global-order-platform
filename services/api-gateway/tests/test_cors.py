"""Browser-origin policy tests."""

from typing import Any


def test_configured_frontend_origin_can_call_gateway(client: Any) -> None:
    response = client.request(
        "OPTIONS",
        "/api/v1/customers/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,x-request-id",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "Authorization" in response.headers["access-control-allow-headers"]


def test_unconfigured_origin_is_not_allowed(client: Any) -> None:
    response = client.request(
        "OPTIONS",
        "/api/v1/customers/me",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
