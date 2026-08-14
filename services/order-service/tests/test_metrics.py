"""Order HTTP and checkout business metric tests."""

from typing import Any
from uuid import UUID, uuid4


def test_metrics_count_failed_checkout_and_hide_dynamic_identifiers(
    client: Any, auth_headers: Any
) -> None:
    headers = auth_headers()
    client.get("/api/v1/carts/me", headers=headers)
    checkout = client.post(
        "/api/v1/orders/checkout",
        headers={**headers, "Idempotency-Key": "metrics-checkout-key"},
    )
    assert checkout.status_code == 400
    dynamic_id = str(uuid4())
    assert client.get(f"/api/v1/orders/me/{dynamic_id}", headers=headers).status_code == 404

    body = client.get("/metrics").text
    assert "shopsphere_http_requests_total" in body
    assert 'route="/api/v1/orders/me/{order_id}"' in body
    assert "shopsphere_order_checkout_attempts_total" in body
    assert "shopsphere_order_checkout_results_total" in body
    assert 'result="failure"' in body
    assert dynamic_id not in body
    assert "metrics-checkout-key" not in body


def test_successful_checkout_counter_increments(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    product_id = UUID("00000000-0000-0000-0000-000000000999")
    catalogue_client.add_product(product_id)
    headers = auth_headers()
    assert (
        client.post(
            "/api/v1/carts/me/items",
            headers=headers,
            json={"product_id": str(product_id), "quantity": 1},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/orders/checkout",
            headers={**headers, "Idempotency-Key": "metrics-success-key"},
        ).status_code
        == 201
    )

    body = client.get("/metrics").text
    assert 'shopsphere_order_checkout_results_total{environment="test",result="success"' in body
