"""Recoverable at-least-once Kafka relay for committed order outbox events."""

import asyncio
import json
import logging
from typing import Any, Protocol
from uuid import UUID

from app.domain.models import OrderDomainEvent

logger = logging.getLogger(__name__)


class OutboxStore(Protocol):
    async def claim(self, batch_size: int, lease_seconds: int) -> list[OrderDomainEvent]: ...
    async def mark_published(self, event_id: UUID) -> None: ...
    async def release_for_retry(self, event_id: UUID, delay: float, code: str) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: OrderDomainEvent) -> None: ...
    async def close(self) -> None: ...


class KafkaEventPublisher:
    def __init__(self, bootstrap_servers: str, client_id: str, timeout_ms: int) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._timeout_ms = timeout_ms
        self._producer: Any | None = None

    async def publish(self, event: OrderDomainEvent) -> None:
        if self._producer is None:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                client_id=self._client_id,
                acks="all",
                enable_idempotence=True,
                request_timeout_ms=self._timeout_ms,
            )
            await self._producer.start()
        try:
            await self._producer.send_and_wait(
                event.event_type,
                key=str(event.aggregate_id).encode(),
                value=json.dumps(event.as_dict(), separators=(",", ":"), sort_keys=True).encode(),
            )
        except Exception:
            await self.close()
            raise

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None


class OutboxRelay:
    def __init__(self, store: OutboxStore, publisher: EventPublisher) -> None:
        self._store = store
        self._publisher = publisher

    async def dispatch_once(self) -> int:
        published = 0
        for event in await self._store.claim(50, 60):
            try:
                await self._publisher.publish(event)
                await self._store.mark_published(event.event_id)
                published += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                await self._store.release_for_retry(event.event_id, 2.0, "kafka_publish_failed")
                logger.warning(
                    "order_event_publish_deferred",
                    extra={
                        "event": "order_event_publish_deferred",
                        "event_id": str(event.event_id),
                    },
                )
        return published

    async def run(self) -> None:
        while True:
            try:
                await self.dispatch_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "order_outbox_poll_failed", extra={"event": "order_outbox_poll_failed"}
                )
            await asyncio.sleep(2.0)

    async def close(self) -> None:
        await self._publisher.close()
