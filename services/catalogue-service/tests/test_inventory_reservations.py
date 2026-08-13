"""Inventory reservation atomicity, idempotency, security, cache, and event tests."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from app.application.outbox import OutboxRelay
from app.application.reservations import InventoryReservationService
from app.core.errors import InvalidOperationError
from app.core.security import Principal
from app.domain.events import (
    INVENTORY_RESERVATION_CONSUMED,
    INVENTORY_RESERVATION_RELEASED,
    INVENTORY_RESERVED,
    DomainEvent,
)


def _stocked_product(
    client: Any, auth_headers: Any, *, suffix: str, quantity: int = 10
) -> dict[str, Any]:
    category = client.post(
        "/api/v1/categories",
        headers=auth_headers("operations_admin"),
        json={"name": f"Reservation {suffix}", "slug": f"reservation-{suffix}"},
    )
    product = client.post(
        "/api/v1/products",
        headers=auth_headers("operations_admin"),
        json={
            "sku": f"RES-{suffix.upper()}",
            "name": f"Reservation Product {suffix}",
            "category_id": category.json()["id"],
            "status": "active",
            "is_searchable": True,
        },
    )
    initialized = client.post(
        f"/api/v1/inventory/products/{product.json()['id']}/initialize",
        headers=auth_headers("operations_admin"),
        json={
            "quantity_on_hand": quantity,
            "reorder_threshold": 1,
            "reason": "Synthetic reservation test stock",
            "idempotency_key": f"reservation-initial-{suffix}",
        },
    )
    assert initialized.status_code == 201
    return product.json()


def _reserve(
    client: Any,
    auth_headers: Any,
    product_id: str,
    *,
    quantity: int,
    reference: str,
    role: str = "order_service",
) -> Any:
    return client.post(
        "/api/v1/inventory/reservations",
        headers={**auth_headers(role), "X-Request-ID": f"correlation-{reference}"},
        json={
            "product_id": product_id,
            "quantity": quantity,
            "external_reference": reference,
        },
    )


def test_successful_reservation_and_reconciliation_read(client: Any, auth_headers: Any) -> None:
    product = _stocked_product(client, auth_headers, suffix="success", quantity=10)

    created = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=4,
        reference="order-workflow-success",
    )
    reservation_id = created.json()["reservation"]["reservation_id"]
    retrieved = client.get(
        f"/api/v1/inventory/reservations/{reservation_id}",
        headers=auth_headers("order_service"),
    )

    assert created.status_code == 201
    assert created.json()["reservation"]["status"] == "ACTIVE"
    assert created.json()["inventory"]["quantity_reserved"] == 4
    assert created.json()["inventory"]["quantity_available"] == 6
    assert created.json()["movement"]["movement_type"] == "RESERVATION"
    assert created.json()["movement"]["reserved_delta"] == 4
    assert retrieved.status_code == 200
    assert retrieved.json() == created.json()["reservation"]


def test_insufficient_stock_never_changes_balances(client: Any, auth_headers: Any) -> None:
    product = _stocked_product(client, auth_headers, suffix="insufficient", quantity=3)

    rejected = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=4,
        reference="order-workflow-insufficient",
    )
    inventory = client.get(
        f"/api/v1/inventory/products/{product['id']}", headers=auth_headers("support")
    )

    assert rejected.status_code == 400
    assert inventory.json()["quantity_reserved"] == 0
    assert inventory.json()["quantity_available"] == 3


def test_duplicate_external_reference_is_idempotent_and_payload_bound(
    client: Any, auth_headers: Any
) -> None:
    product = _stocked_product(client, auth_headers, suffix="duplicate", quantity=8)
    first = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=3,
        reference="order-workflow-duplicate",
    )
    replay = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=3,
        reference="order-workflow-duplicate",
    )
    conflict = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=2,
        reference="order-workflow-duplicate",
    )

    assert first.status_code == replay.status_code == 201
    assert (
        first.json()["reservation"]["reservation_id"]
        == replay.json()["reservation"]["reservation_id"]
    )
    assert first.json()["movement"]["id"] == replay.json()["movement"]["id"]
    assert replay.json()["inventory"]["quantity_reserved"] == 3
    assert conflict.status_code == 409


def test_release_and_duplicate_release_are_idempotent(client: Any, auth_headers: Any) -> None:
    product = _stocked_product(client, auth_headers, suffix="release", quantity=5)
    reservation = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=5,
        reference="order-workflow-release",
    ).json()["reservation"]
    path = f"/api/v1/inventory/reservations/{reservation['reservation_id']}/release"

    first = client.post(path, headers=auth_headers("order_service"))
    replay = client.post(path, headers=auth_headers("order_service"))

    assert first.status_code == replay.status_code == 200
    assert first.json()["reservation"]["status"] == "RELEASED"
    assert first.json()["inventory"]["quantity_reserved"] == 0
    assert first.json()["inventory"]["quantity_available"] == 5
    assert first.json()["movement"]["id"] == replay.json()["movement"]["id"]


def test_consumption_finalizes_allocation_without_claiming_shipment(
    client: Any, auth_headers: Any
) -> None:
    product = _stocked_product(client, auth_headers, suffix="consume", quantity=7)
    reservation = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=2,
        reference="order-workflow-consume",
    ).json()["reservation"]

    consumed = client.post(
        f"/api/v1/inventory/reservations/{reservation['reservation_id']}/consume",
        headers=auth_headers("order_service"),
    )

    assert consumed.status_code == 200
    assert consumed.json()["reservation"]["status"] == "CONSUMED"
    assert consumed.json()["inventory"]["quantity_on_hand"] == 5
    assert consumed.json()["inventory"]["quantity_reserved"] == 0
    assert consumed.json()["movement"]["movement_type"] == "FULFILMENT"


def test_final_unit_concurrency_allows_only_one_reservation(client: Any, auth_headers: Any) -> None:
    product = _stocked_product(client, auth_headers, suffix="race", quantity=1)
    service = InventoryReservationService(client.application.state.unit_of_work_factory)
    actor = Principal(
        subject="order-service-race",
        username="order-service",
        email=None,
        roles=frozenset({"order_service"}),
    )

    async def reserve(reference: str) -> object:
        try:
            return await service.reserve(
                actor,
                UUID(product["id"]),
                1,
                reference,
                reference,
            )
        except InvalidOperationError as exc:
            return exc

    async def run_concurrently() -> list[object]:
        return list(
            await asyncio.gather(
                reserve("order-final-unit-a"),
                reserve("order-final-unit-b"),
            )
        )

    results = client._loop.run_until_complete(run_concurrently())  # type: ignore[attr-defined]
    inventory = client.get(
        f"/api/v1/inventory/products/{product['id']}", headers=auth_headers("support")
    )

    assert sum(isinstance(result, InvalidOperationError) for result in results) == 1
    assert inventory.json()["quantity_reserved"] == 1
    assert inventory.json()["quantity_available"] == 0


def test_reservation_invalidates_cached_availability(client: Any, auth_headers: Any) -> None:
    product = _stocked_product(client, auth_headers, suffix="cache", quantity=6)
    path = f"/api/v1/inventory/products/{product['id']}/availability"
    before = client.get(path, headers=auth_headers("customer"))
    reserved = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=2,
        reference="order-workflow-cache",
    )
    after = client.get(path, headers=auth_headers("customer"))

    assert before.json()["quantity_available"] == 6
    assert reserved.status_code == 201
    assert after.json()["quantity_available"] == 4


def test_customer_and_support_cannot_mutate_reservations(client: Any, auth_headers: Any) -> None:
    product = _stocked_product(client, auth_headers, suffix="auth", quantity=4)

    customer = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=1,
        reference="customer-reservation-denied",
        role="customer",
    )
    support = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=1,
        reference="support-reservation-denied",
        role="support",
    )

    assert customer.status_code == support.status_code == 403


def test_reservation_lifecycle_events_are_safe_and_transactionally_staged(
    client: Any, auth_headers: Any
) -> None:
    product = _stocked_product(client, auth_headers, suffix="events", quantity=4)
    created = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=1,
        reference="order-workflow-events",
    )
    reservation_id = created.json()["reservation"]["reservation_id"]
    client.post(
        f"/api/v1/inventory/reservations/{reservation_id}/release",
        headers=auth_headers("order_service"),
    )
    events = client.application.state.test_outbox_events
    lifecycle = [
        event
        for event in events
        if event.event_type in {INVENTORY_RESERVED, INVENTORY_RESERVATION_RELEASED}
    ]

    assert [event.event_type for event in lifecycle] == [
        INVENTORY_RESERVED,
        INVENTORY_RESERVATION_RELEASED,
    ]
    assert all(event.aggregate_id == UUID(reservation_id) for event in lifecycle)
    assert all("external_reference" not in event.payload for event in lifecycle)
    assert all(
        not any(term in str(event.as_dict()).casefold() for term in ("password", "jwt", "token"))
        for event in lifecycle
    )


class _RetryStore:
    def __init__(self, event: DomainEvent) -> None:
        self.event = event
        self.retries: list[str] = []

    async def claim(self, batch_size: int, lease_seconds: int) -> list[DomainEvent]:
        return [self.event]

    async def mark_published(self, event_id: object) -> None:
        raise AssertionError("Unavailable Kafka must not acknowledge publication")

    async def release_for_retry(
        self, event_id: object, delay_seconds: float, error_code: str
    ) -> None:
        self.retries.append(error_code)


class _UnavailablePublisher:
    async def publish(self, event: DomainEvent) -> None:
        raise ConnectionError("simulated Kafka outage")

    async def close(self) -> None:
        return None


def test_kafka_unavailable_keeps_reservation_event_retryable(
    client: Any, auth_headers: Any
) -> None:
    product = _stocked_product(client, auth_headers, suffix="kafka", quantity=3)
    created = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=1,
        reference="order-workflow-kafka",
    )
    event = next(
        event
        for event in client.application.state.test_outbox_events
        if event.event_type == INVENTORY_RESERVED
    )
    store = _RetryStore(event)
    relay = OutboxRelay(
        store,
        _UnavailablePublisher(),
        batch_size=1,
        poll_interval_seconds=1,
        retry_base_seconds=1,
        lease_seconds=30,
    )

    published = client._loop.run_until_complete(relay.dispatch_once())  # type: ignore[attr-defined]

    assert created.status_code == 201
    assert created.json()["inventory"]["quantity_reserved"] == 1
    assert published == 0
    assert store.retries == ["kafka_publish_failed"]
    assert event.event_type == INVENTORY_RESERVED


def test_consumed_event_contract_exists(client: Any, auth_headers: Any) -> None:
    product = _stocked_product(client, auth_headers, suffix="consumed-event", quantity=2)
    reservation_id = _reserve(
        client,
        auth_headers,
        product["id"],
        quantity=1,
        reference="order-workflow-consumed-event",
    ).json()["reservation"]["reservation_id"]
    client.post(
        f"/api/v1/inventory/reservations/{reservation_id}/consume",
        headers=auth_headers("operations_admin"),
    )

    assert INVENTORY_RESERVATION_CONSUMED in {
        event.event_type for event in client.application.state.test_outbox_events
    }
