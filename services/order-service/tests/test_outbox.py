"""Order event contracts and established at-least-once outbox behavior."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.application.outbox import OutboxRelay
from app.domain.events import (
    EVENT_VERSION,
    ORDER_CANCELLED,
    ORDER_CONFIRMED,
    ORDER_CREATED,
    ORDER_STATUS_CHANGED,
    DomainEvent,
    order_cancelled,
    order_confirmed,
    order_created,
    order_status_changed,
)
from app.domain.models import Order, OrderStatus


def _order(status: OrderStatus = OrderStatus.CONFIRMED) -> Order:
    return Order(
        customer_identity_subject="synthetic-customer",
        source_cart_id=uuid4(),
        order_number="SS-SYNTHETIC",
        currency_code="USD",
        subtotal=Decimal("19.9900"),
        total=Decimal("19.9900"),
        status=status,
    )


def test_event_envelope_is_versioned_serializable_and_safe() -> None:
    event = order_created(_order(), 2, "contract-correlation")
    encoded = json.dumps(event.as_dict()).casefold()

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
    assert event.event_type == ORDER_CREATED
    assert event.event_version == EVENT_VERSION == 1
    assert event.aggregate_type == "order"
    assert event.correlation_id == "contract-correlation"
    assert event.producer == "order-service"
    assert event.as_dict()["occurred_at"].endswith("Z")
    assert not any(
        term in encoded
        for term in (
            "password",
            "jwt",
            "access_token",
            "refresh_token",
            "client_secret",
            "customer_identity_subject",
            "synthetic-customer",
        )
    )


def test_all_order_event_contracts_are_versioned_and_correlated() -> None:
    confirmed = _order()
    processing = replace(confirmed, status=OrderStatus.PROCESSING)
    cancelled = replace(confirmed, status=OrderStatus.CANCELLED)
    events = [
        order_created(confirmed, 1, "created-correlation"),
        order_confirmed(confirmed, "confirmed-correlation"),
        order_status_changed(processing, "CONFIRMED", "status-correlation"),
        order_cancelled(cancelled, "cancel-correlation"),
    ]

    assert [event.event_type for event in events] == [
        ORDER_CREATED,
        ORDER_CONFIRMED,
        ORDER_STATUS_CHANGED,
        ORDER_CANCELLED,
    ]
    assert [event.correlation_id for event in events] == [
        "created-correlation",
        "confirmed-correlation",
        "status-correlation",
        "cancel-correlation",
    ]
    assert all(event.event_version == 1 for event in events)
    encoded = json.dumps([event.as_dict() for event in events]).casefold()
    assert not any(
        term in encoded
        for term in (
            "password",
            "jwt",
            "access_token",
            "refresh_token",
            "client_secret",
            "customer_identity_subject",
            "synthetic-customer",
        )
    )
    assert events[2].payload == {
        "order_id": str(confirmed.id),
        "order_number": confirmed.order_number,
        "previous_status": "CONFIRMED",
        "status": "PROCESSING",
    }


class Publisher:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.published: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        if self.fail:
            raise ConnectionError("simulated Kafka outage")
        self.published.append(event)

    async def close(self) -> None:
        return None


class RetryStore:
    def __init__(self, event: DomainEvent, *, fail_ack_once: bool = False) -> None:
        self.event = event
        self.acknowledged = False
        self.fail_ack_once = fail_ack_once
        self.claims: list[tuple[int, int]] = []
        self.retries: list[tuple[object, float, str]] = []

    async def claim(self, batch_size: int, lease_seconds: int) -> list[DomainEvent]:
        self.claims.append((batch_size, lease_seconds))
        return [] if self.acknowledged else [self.event]

    async def mark_published(self, event_id: object) -> None:
        if self.fail_ack_once:
            self.fail_ack_once = False
            raise RuntimeError("simulated post-publication database failure")
        self.acknowledged = True

    async def release_for_retry(
        self, event_id: object, delay_seconds: float, error_code: str
    ) -> None:
        self.retries.append((event_id, delay_seconds, error_code))


def _relay(store: RetryStore, publisher: Publisher) -> OutboxRelay:
    return OutboxRelay(
        store,
        publisher,
        batch_size=10,
        poll_interval_seconds=1,
        retry_base_seconds=1,
        lease_seconds=30,
    )


def test_confirmed_publication_is_acknowledged_and_observable(caplog: Any) -> None:
    caplog.set_level(logging.INFO)
    event = order_confirmed(_order(), "published-correlation")
    store = RetryStore(event)
    publisher = Publisher()

    assert asyncio.run(_relay(store, publisher).dispatch_once()) == 1
    assert store.acknowledged is True
    assert publisher.published == [event]
    assert store.claims == [(10, 30)]
    assert "domain_event_published" in caplog.text


def test_kafka_unavailable_keeps_committed_event_pending_for_retry(caplog: Any) -> None:
    event = order_created(_order(), 1, "kafka-outage")
    store = RetryStore(event)

    assert asyncio.run(_relay(store, Publisher(fail=True)).dispatch_once()) == 0
    assert store.acknowledged is False
    assert store.retries == [(event.event_id, 2, "kafka_publish_failed")]
    assert "domain_event_publish_deferred" in caplog.text


def test_post_publish_ack_failure_can_duplicate_same_event_id_on_retry() -> None:
    event = order_cancelled(
        replace(_order(), status=OrderStatus.CANCELLED), "duplicate-correlation"
    )
    store = RetryStore(event, fail_ack_once=True)
    publisher = Publisher()
    relay = _relay(store, publisher)

    assert asyncio.run(relay.dispatch_once()) == 0
    assert asyncio.run(relay.dispatch_once()) == 1
    assert [published.event_id for published in publisher.published] == [
        event.event_id,
        event.event_id,
    ]
    assert store.acknowledged is True
    assert store.retries[0][2] == "kafka_publish_failed"


def test_kafka_failure_does_not_change_committed_order(
    client: Any,
    auth_headers: Any,
    catalogue_client: Any,
    store: dict[str, Any],
) -> None:
    product_id = uuid4()
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
    checked_out = client.post(
        "/api/v1/orders/checkout",
        headers={**headers, "Idempotency-Key": "kafka-independent-commit"},
    )
    assert checked_out.status_code == 201
    order_id = checked_out.json()["order_id"]
    created = next(event for event in store["outbox"].values() if event.event_type == ORDER_CREATED)

    retry_store = RetryStore(created)
    assert asyncio.run(_relay(retry_store, Publisher(fail=True)).dispatch_once()) == 0

    detail = client.get(f"/api/v1/orders/me/{order_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "CONFIRMED"
    assert UUID(order_id) in store["orders"]
