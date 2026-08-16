"""Order history, IDOR, role policy, transitions, cancellation, audit and events."""

from typing import Any
from uuid import UUID

from app.domain.events import ORDER_CANCELLED, ORDER_STATUS_CHANGED


def _create_order(
    client: Any,
    auth_headers: Any,
    catalogue_client: Any,
    product_id: UUID,
    *,
    subject: str = "customer-a",
    key: str = "lifecycle-checkout",
) -> tuple[dict[str, str], dict[str, Any]]:
    catalogue_client.add_product(product_id, quantity_available=50)
    headers = auth_headers(subject)
    added = client.post(
        "/api/v1/carts/me/items",
        headers=headers,
        json={"product_id": str(product_id), "quantity": 2},
    )
    assert added.status_code == 201
    response = client.post(
        "/api/v1/orders/checkout",
        headers={**headers, "Idempotency-Key": key},
    )
    assert response.status_code == 201
    return headers, response.json()


def test_customer_order_list_detail_history_and_pagination(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    headers, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000201"),
    )
    page = client.get("/api/v1/orders/me?status=CONFIRMED&offset=0&limit=1", headers=headers)
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["order_id"] == order["order_id"]

    detail = client.get(f"/api/v1/orders/me/{order['order_id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["items"] == order["items"]
    history = client.get(f"/api/v1/orders/me/{order['order_id']}/history", headers=headers)
    assert history.status_code == 200
    assert history.json()["current_status"] == "CONFIRMED"
    assert [entry["status"] for entry in history.json()["items"]] == ["CONFIRMED"]


def test_cross_customer_order_access_is_hidden(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    _, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000202"),
    )
    other = auth_headers("customer-b")
    assert client.get(f"/api/v1/orders/me/{order['order_id']}", headers=other).status_code == 404
    assert (
        client.get(f"/api/v1/orders/me/{order['order_id']}/history", headers=other).status_code
        == 404
    )


def test_admin_valid_transition_appends_history_audit_event_and_consumes_inventory(
    client: Any,
    auth_headers: Any,
    catalogue_client: Any,
    store: dict[str, Any],
) -> None:
    _, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000203"),
    )
    admin = auth_headers("admin-a", "operations_admin")
    processing = client.post(
        f"/api/v1/orders/admin/{order['order_id']}/status",
        headers={**admin, "X-Request-ID": "transition-correlation"},
        json={"target_status": "PROCESSING"},
    )
    assert processing.status_code == 200
    fulfilled = client.post(
        f"/api/v1/orders/admin/{order['order_id']}/status",
        headers=admin,
        json={"target_status": "FULFILLED"},
    )
    assert fulfilled.status_code == 200
    assert fulfilled.json()["status"] == "FULFILLED"
    assert len(catalogue_client.consume_calls) == 1

    history = client.get(f"/api/v1/orders/admin/{order['order_id']}/history", headers=admin).json()
    assert [entry["status"] for entry in history["items"]] == [
        "CONFIRMED",
        "PROCESSING",
        "FULFILLED",
    ]
    assert history["items"][0]["status"] == "CONFIRMED"
    status_events = [
        event for event in store["outbox"].values() if event.event_type == ORDER_STATUS_CHANGED
    ]
    assert len(status_events) == 2
    assert status_events[0].correlation_id == "transition-correlation"
    metrics = client.get("/metrics").text
    assert 'shopsphere_order_transitions_total{environment="test",result="success"' in metrics
    assert 'target_status="PROCESSING"' in metrics
    assert 'target_status="FULFILLED"' in metrics


def test_invalid_and_arbitrary_transitions_are_rejected(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    _, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000204"),
    )
    admin = auth_headers("admin-a", "operations_admin")
    invalid = client.post(
        f"/api/v1/orders/admin/{order['order_id']}/status",
        headers=admin,
        json={"target_status": "FULFILLED"},
    )
    assert invalid.status_code == 400
    arbitrary = client.post(
        f"/api/v1/orders/admin/{order['order_id']}/status",
        headers=admin,
        json={"target_status": "SHIPPED"},
    )
    assert arbitrary.status_code == 422


def test_customer_cancellation_releases_inventory_and_is_idempotent(
    client: Any,
    auth_headers: Any,
    catalogue_client: Any,
    store: dict[str, Any],
) -> None:
    headers, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000205"),
    )
    path = f"/api/v1/orders/me/{order['order_id']}/cancellation"
    first = client.post(path, headers=headers)
    second = client.post(path, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "CANCELLED"
    assert len(catalogue_client.release_calls) == 1
    event_types = [event.event_type for event in store["outbox"].values()]
    assert event_types.count(ORDER_STATUS_CHANGED) == 1
    assert event_types.count(ORDER_CANCELLED) == 1
    history = client.get(f"/api/v1/orders/me/{order['order_id']}/history", headers=headers).json()
    assert [entry["status"] for entry in history["items"]] == ["CONFIRMED", "CANCELLED"]


def test_fulfilled_order_cannot_be_cancelled(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    customer, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000206"),
    )
    admin = auth_headers("admin-a", "operations_admin")
    for target in ("PROCESSING", "FULFILLED"):
        assert (
            client.post(
                f"/api/v1/orders/admin/{order['order_id']}/status",
                headers=admin,
                json={"target_status": target},
            ).status_code
            == 200
        )
    assert (
        client.post(
            f"/api/v1/orders/me/{order['order_id']}/cancellation", headers=customer
        ).status_code
        == 400
    )


def test_cancellation_release_failure_preserves_current_status(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    customer, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000209"),
    )
    catalogue_client.fail_release = True
    response = client.post(f"/api/v1/orders/me/{order['order_id']}/cancellation", headers=customer)
    assert response.status_code == 503
    detail = client.get(f"/api/v1/orders/me/{order['order_id']}", headers=customer)
    assert detail.json()["status"] == "CONFIRMED"


def test_support_can_read_but_cannot_mutate(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    _, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000207"),
    )
    support = auth_headers("support-a", "support")
    assert client.get("/api/v1/orders/admin", headers=support).status_code == 200
    assert (
        client.get(f"/api/v1/orders/admin/{order['order_id']}", headers=support).status_code == 200
    )
    assert (
        client.post(
            f"/api/v1/orders/admin/{order['order_id']}/status",
            headers=support,
            json={"target_status": "PROCESSING"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/orders/admin/{order['order_id']}/cancellation", headers=support
        ).status_code
        == 403
    )


def test_audit_visibility_is_authorized_and_safe(
    client: Any, auth_headers: Any, catalogue_client: Any
) -> None:
    customer, order = _create_order(
        client,
        auth_headers,
        catalogue_client,
        UUID("00000000-0000-0000-0000-000000000208"),
    )
    own = client.get(f"/api/v1/orders/me/{order['order_id']}/audit?limit=2", headers=customer)
    assert own.status_code == 200
    assert own.json()["total"] == 4
    assert all(entry["actor_subject"] == "customer:self" for entry in own.json()["items"])
    assert "token" not in str(own.json()).lower()

    support = auth_headers("support-a", "support")
    operational = client.get(f"/api/v1/orders/admin/{order['order_id']}/audit", headers=support)
    assert operational.status_code == 200
    assert operational.json()["total"] == 4
    other = auth_headers("customer-b")
    assert (
        client.get(f"/api/v1/orders/me/{order['order_id']}/audit", headers=other).status_code == 404
    )
