"""Versioned event contracts and recoverable outbox delivery behavior."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.application.outbox import OutboxRelay
from app.domain.events import (
    INVENTORY_ADJUSTED,
    INVENTORY_LOW,
    INVENTORY_OUT_OF_STOCK,
    PRICE_CHANGED,
    PRODUCT_CREATED,
    PRODUCT_UPDATED,
    DomainEvent,
)
from app.domain.models import Product, ProductStatus


def _create_product(client: Any, auth_headers: Any, suffix: str = "event") -> dict[str, Any]:
    category = client.post(
        "/api/v1/categories",
        headers=auth_headers("operations_admin"),
        json={"name": f"Event Category {suffix}", "slug": f"event-category-{suffix}"},
    )
    response = client.post(
        "/api/v1/products",
        headers={**auth_headers("operations_admin"), "X-Request-ID": f"product-{suffix}"},
        json={
            "sku": f"EVENT-{suffix.upper()}",
            "name": f"Event Product {suffix}",
            "category_id": category.json()["id"],
            "status": "active",
            "is_searchable": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_event_envelope_is_versioned_serializable_and_contains_no_credentials() -> None:
    product = Product(
        sku="EVENT-001",
        name="Event Product",
        category_id=uuid4(),
        status=ProductStatus.ACTIVE,
        is_searchable=True,
    )
    event = DomainEvent(
        event_type=PRODUCT_CREATED,
        aggregate_type="product",
        aggregate_id=product.id,
        correlation_id="event-contract",
        payload={"product_id": str(product.id), "sku": product.sku},
    )

    encoded = json.dumps(event.as_dict())

    assert event.as_dict().keys() == {
        "event_id",
        "event_type",
        "event_version",
        "aggregate_type",
        "aggregate_id",
        "occurred_at",
        "correlation_id",
        "producer",
        "payload",
    }
    assert event.event_version == 1
    assert event.occurred_at.tzinfo is not None
    assert not any(term in encoded.casefold() for term in ("password", "jwt", "token", "secret"))


def test_product_created_updated_and_price_changed_are_saved_to_outbox(
    client: Any, auth_headers: Any
) -> None:
    product = _create_product(client, auth_headers)
    updated = client.patch(
        f"/api/v1/products/{product['id']}",
        headers={**auth_headers("operations_admin"), "X-Request-ID": "product-update"},
        json={"name": "Updated Event Product"},
    )
    priced = client.put(
        f"/api/v1/products/{product['id']}/prices/USD",
        headers={**auth_headers("operations_admin"), "X-Request-ID": "price-change"},
        json={"amount": "19.9900"},
    )

    events = client.application.state.test_outbox_events
    assert updated.status_code == 200
    assert priced.status_code == 200
    assert [event.event_type for event in events] == [
        PRODUCT_CREATED,
        PRODUCT_UPDATED,
        PRICE_CHANGED,
    ]
    assert events[0].correlation_id == "product-event"
    assert events[1].payload["changed_fields"] == ["name"]
    assert events[2].payload["amount"] == format(Decimal("19.9900"), "f")


def test_inventory_adjusted_low_and_out_of_stock_events_follow_transitions(
    client: Any, auth_headers: Any
) -> None:
    product = _create_product(client, auth_headers, "stock")
    initialized = client.post(
        f"/api/v1/inventory/products/{product['id']}/initialize",
        headers={**auth_headers("operations_admin"), "X-Request-ID": "stock-init"},
        json={
            "quantity_on_hand": 3,
            "reorder_threshold": 2,
            "reason": "Opening stock",
            "idempotency_key": "event-stock-init",
        },
    )
    low = client.post(
        f"/api/v1/inventory/products/{product['id']}/adjustments",
        headers={**auth_headers("operations_admin"), "X-Request-ID": "stock-low"},
        json={
            "movement_type": "DAMAGE",
            "quantity_delta": -1,
            "reason": "Damage",
            "idempotency_key": "event-stock-low",
        },
    )
    empty = client.post(
        f"/api/v1/inventory/products/{product['id']}/adjustments",
        headers={**auth_headers("operations_admin"), "X-Request-ID": "stock-empty"},
        json={
            "movement_type": "DAMAGE",
            "quantity_delta": -2,
            "reason": "Damage",
            "idempotency_key": "event-stock-empty",
        },
    )

    event_types = [event.event_type for event in client.application.state.test_outbox_events]
    assert initialized.status_code == 201
    assert low.status_code == 200
    assert empty.status_code == 200
    assert event_types.count(INVENTORY_ADJUSTED) == 3
    assert event_types.count(INVENTORY_LOW) == 1
    assert event_types.count(INVENTORY_OUT_OF_STOCK) == 1


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.published.append(event)

    async def close(self) -> None:
        return None


class RetryStore:
    def __init__(self, event: DomainEvent) -> None:
        self.event = event
        self.published = False
        self.fail_ack_once = True
        self.retries: list[tuple[object, float, str]] = []

    async def claim(self, batch_size: int, lease_seconds: int) -> list[DomainEvent]:
        return [] if self.published else [self.event]

    async def mark_published(self, event_id: object) -> None:
        if self.fail_ack_once:
            self.fail_ack_once = False
            raise RuntimeError("simulated post-publish database failure")
        self.published = True

    async def release_for_retry(
        self, event_id: object, delay_seconds: float, error_code: str
    ) -> None:
        self.retries.append((event_id, delay_seconds, error_code))


def test_retry_can_duplicate_an_event_and_preserves_the_same_event_id() -> None:
    event = DomainEvent(
        event_type=PRODUCT_CREATED,
        aggregate_type="product",
        aggregate_id=uuid4(),
        correlation_id="duplicate-proof",
        payload={"sku": "DUPLICATE-001"},
    )
    store = RetryStore(event)
    publisher = FakePublisher()
    relay = OutboxRelay(
        store,
        publisher,
        batch_size=10,
        poll_interval_seconds=1,
        retry_base_seconds=1,
        lease_seconds=30,
    )

    assert asyncio.run(relay.dispatch_once()) == 0
    assert asyncio.run(relay.dispatch_once()) == 1
    assert [item.event_id for item in publisher.published] == [event.event_id, event.event_id]
    assert store.retries[0][2] == "kafka_publish_failed"


class UnavailablePublisher(FakePublisher):
    async def publish(self, event: DomainEvent) -> None:
        raise ConnectionError("simulated Kafka outage")


def test_kafka_unavailable_leaves_committed_event_retryable() -> None:
    event = DomainEvent(
        event_type=PRICE_CHANGED,
        aggregate_type="product",
        aggregate_id=uuid4(),
        correlation_id="kafka-outage",
        payload={"amount": "10.0000", "currency_code": "USD"},
    )
    store = RetryStore(event)
    store.fail_ack_once = False
    relay = OutboxRelay(
        store,
        UnavailablePublisher(),
        batch_size=10,
        poll_interval_seconds=1,
        retry_base_seconds=1,
        lease_seconds=30,
    )

    assert asyncio.run(relay.dispatch_once()) == 0
    assert store.published is False
    assert store.retries[0][2] == "kafka_publish_failed"
