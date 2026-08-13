"""At-least-once order outbox delivery behavior."""

import asyncio
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.application.outbox import OutboxRelay
from app.domain.events import order_created
from app.domain.models import Order


class MemoryStore:
    def __init__(self, event: Any) -> None:
        self.event = event
        self.published: list[Any] = []
        self.retries: list[tuple[Any, str]] = []

    async def claim(self, batch_size: int, lease_seconds: int) -> list[Any]:
        assert batch_size == 50 and lease_seconds == 60
        return [self.event]

    async def mark_published(self, event_id: Any) -> None:
        self.published.append(event_id)

    async def release_for_retry(self, event_id: Any, delay: float, code: str) -> None:
        assert delay > 0
        self.retries.append((event_id, code))


class Publisher:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def publish(self, event: Any) -> None:
        if self.fail:
            raise RuntimeError("simulated Kafka outage")

    async def close(self) -> None:
        return None


def _event() -> Any:
    order = Order(
        customer_identity_subject="synthetic-customer",
        source_cart_id=uuid4(),
        order_number="SS-SYNTHETIC",
        currency_code="USD",
        subtotal=Decimal("1.0000"),
        total=Decimal("1.0000"),
    )
    return order_created(order, 1, "synthetic-correlation")


def test_outbox_acknowledges_confirmed_publication() -> None:
    store = MemoryStore(_event())
    assert asyncio.run(OutboxRelay(store, Publisher()).dispatch_once()) == 1
    assert store.published == [store.event.event_id]
    assert store.retries == []


def test_kafka_failure_releases_event_for_retry() -> None:
    store = MemoryStore(_event())
    assert asyncio.run(OutboxRelay(store, Publisher(fail=True)).dispatch_once()) == 0
    assert store.published == []
    assert store.retries == [(store.event.event_id, "kafka_publish_failed")]
