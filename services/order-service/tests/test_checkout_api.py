"""Checkout workflow, security, idempotency, Saga, and evidence tests."""

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from app.domain.events import ORDER_CONFIRMED, ORDER_CREATED
from app.domain.models import CheckoutAttemptStatus


def _add_item(client: Any, headers: dict[str, str], product_id: UUID, quantity: int = 1) -> None:
    response = client.post(
        "/api/v1/carts/me/items",
        headers=headers,
        json={"product_id": str(product_id), "quantity": quantity},
    )
    assert response.status_code == 201


def _checkout(client: Any, headers: dict[str, str], key: str = "checkout-key-0001") -> Any:
    return client.post(
        "/api/v1/orders/checkout",
        headers={**headers, "Idempotency-Key": key, "X-Request-ID": "checkout-correlation"},
    )


def test_successful_checkout_recalculates_price_and_records_evidence(
    client: Any,
    auth_headers: Any,
    catalogue_client: Any,
    store: dict[str, Any],
) -> None:
    product_id = UUID("00000000-0000-0000-0000-000000000101")
    catalogue_client.add_product(product_id, price="10.1250")
    headers = auth_headers()
    _add_item(client, headers, product_id, 2)
    catalogue_client.add_product(product_id, price="11.3333")

    response = _checkout(client, headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "CONFIRMED"
    assert Decimal(body["items"][0]["unit_price"]) == Decimal("11.3333")
    assert Decimal(body["items"][0]["line_total"]) == Decimal("22.6666")
    assert Decimal(body["subtotal"]) == Decimal("22.6666")
    assert body["total"] == body["subtotal"]
    assert body["payment_status"] == "not_in_scope"
    assert len(store["orders"]) == 1
    assert len(store["history"]) == 1
    assert {event.action for event in store["audits"].values()} == {
        "checkout.initiated",
        "inventory.reserved",
        "order.created",
        "order.confirmed",
    }
    assert {event.event_type for event in store["outbox"].values()} == {
        ORDER_CREATED,
        ORDER_CONFIRMED,
    }
    assert all(event.correlation_id == "checkout-correlation" for event in store["outbox"].values())


def test_empty_cart_is_rejected(client: Any, auth_headers: Any) -> None:
    client.get("/api/v1/carts/me", headers=auth_headers())
    response = _checkout(client, auth_headers())
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_operation"


@pytest.mark.parametrize("active", [False])
def test_inactive_product_is_revalidated_at_checkout(
    client: Any, auth_headers: Any, catalogue_client: Any, active: bool
) -> None:
    product_id = UUID("00000000-0000-0000-0000-000000000102")
    catalogue_client.add_product(product_id)
    _add_item(client, auth_headers(), product_id)
    catalogue_client.add_product(product_id, active=active)
    response = _checkout(client, auth_headers())
    assert response.status_code == 409


def test_insufficient_inventory_is_rejected(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    product_id = UUID("00000000-0000-0000-0000-000000000103")
    catalogue_client.add_product(product_id, quantity_available=5)
    _add_item(client, auth_headers(), product_id, 4)
    catalogue_client.add_product(product_id, quantity_available=2)
    assert _checkout(client, auth_headers()).status_code == 409


def test_multiple_items_and_monetary_precision(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    first = UUID("00000000-0000-0000-0000-000000000104")
    second = UUID("00000000-0000-0000-0000-000000000105")
    catalogue_client.add_product(first, price="0.10005")
    catalogue_client.add_product(second, price="2.33335")
    _add_item(client, auth_headers(), first, 3)
    _add_item(client, auth_headers(), second, 2)
    response = _checkout(client, auth_headers())
    assert response.status_code == 201
    assert Decimal(response.json()["total"]) == Decimal("4.9671")
    assert len(response.json()["items"]) == 2


def test_duplicate_retry_returns_same_order_once(
    client: Any, auth_headers: Any, catalogue_client: Any, store: dict[str, Any]
) -> None:
    product_id = UUID("00000000-0000-0000-0000-000000000106")
    catalogue_client.add_product(product_id)
    headers = auth_headers()
    _add_item(client, headers, product_id)
    first = _checkout(client, headers, "stable-retry-key")
    second = _checkout(client, headers, "stable-retry-key")
    assert first.status_code == second.status_code == 201
    assert first.json()["order_id"] == second.json()["order_id"]
    assert len(store["orders"]) == 1
    assert len(catalogue_client.reserve_calls) == 1


def test_reusing_key_for_new_cart_conflicts(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    first = UUID("00000000-0000-0000-0000-000000000107")
    second = UUID("00000000-0000-0000-0000-000000000108")
    catalogue_client.add_product(first)
    catalogue_client.add_product(second)
    headers = auth_headers()
    _add_item(client, headers, first)
    assert _checkout(client, headers, "conflicting-key").status_code == 201
    _add_item(client, headers, second)
    assert _checkout(client, headers, "conflicting-key").status_code == 409


def test_partial_reservation_failure_releases_prior_line(
    client: Any, auth_headers: Any, catalogue_client: Any, store: dict[str, Any]
) -> None:
    first = UUID("00000000-0000-0000-0000-000000000109")
    second = UUID("00000000-0000-0000-0000-000000000110")
    catalogue_client.add_product(first)
    catalogue_client.add_product(second)
    catalogue_client.fail_reservation_for = second
    headers = auth_headers()
    _add_item(client, headers, first)
    _add_item(client, headers, second)
    response = _checkout(client, headers, "partial-failure")
    assert response.status_code == 409
    assert len(catalogue_client.release_calls) == 1
    attempt = store["attempts"][("customer-a", "partial-failure")]
    assert attempt.status is CheckoutAttemptStatus.FAILED


def test_database_failure_compensates_and_failed_release_is_durable(
    client: Any, auth_headers: Any, catalogue_client: Any, store: dict[str, Any]
) -> None:
    product_id = UUID("00000000-0000-0000-0000-000000000111")
    catalogue_client.add_product(product_id)
    _add_item(client, auth_headers(), product_id)
    store["fail_order_write"] = True
    catalogue_client.fail_release = True
    response = _checkout(client, auth_headers(), "database-failure")
    assert response.status_code == 503
    attempt = store["attempts"][("customer-a", "database-failure")]
    assert attempt.status is CheckoutAttemptStatus.COMPENSATION_REQUIRED
    assert len(attempt.unresolved_reservations) == 1
    assert "reservation_id" in attempt.unresolved_reservations[0]


def test_catalogue_unavailable(client: Any, auth_headers: Any, catalogue_client: Any) -> None:
    product_id = UUID("00000000-0000-0000-0000-000000000112")
    catalogue_client.add_product(product_id)
    _add_item(client, auth_headers(), product_id)
    catalogue_client.unavailable = True
    assert _checkout(client, auth_headers()).status_code == 503


def test_authentication_and_cross_customer_ownership(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    product_id = UUID("00000000-0000-0000-0000-000000000113")
    catalogue_client.add_product(product_id)
    _add_item(client, auth_headers("customer-a"), product_id)
    assert _checkout(client, {}).status_code == 401
    response = _checkout(client, auth_headers("customer-b"), "customer-b-key")
    assert response.status_code == 400
