"""Recoverable PostgreSQL outbox relay with at-least-once Kafka delivery."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Protocol

from aiokafka import AIOKafkaProducer

from app.domain.events import DomainEvent

logger = logging.getLogger(__name__)


class OutboxStore(Protocol):
    async def claim(self, batch_size: int, lease_seconds: int) -> list[DomainEvent]: ...

    async def mark_published(self, event_id: object) -> None: ...

    async def release_for_retry(
        self, event_id: object, delay_seconds: float, error_code: str
    ) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...

    async def close(self) -> None: ...


class KafkaEventPublisher:
    """Lazy producer: broker startup failures never prevent catalogue startup."""

    def __init__(self, bootstrap_servers: str, client_id: str, request_timeout_ms: int) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._request_timeout_ms = request_timeout_ms
        self._producer: AIOKafkaProducer | None = None

    async def _producer_instance(self) -> AIOKafkaProducer:
        if self._producer is None:
            producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                client_id=self._client_id,
                acks="all",
                enable_idempotence=True,
                request_timeout_ms=self._request_timeout_ms,
            )
            await producer.start()
            self._producer = producer
        return self._producer

    async def publish(self, event: DomainEvent) -> None:
        try:
            producer = await self._producer_instance()
            await producer.send_and_wait(
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
    """Polls committed events and acknowledges each only after Kafka confirms it."""

    def __init__(
        self,
        store: OutboxStore,
        publisher: EventPublisher,
        *,
        batch_size: int,
        poll_interval_seconds: float,
        retry_base_seconds: float,
        lease_seconds: int,
    ) -> None:
        self._store = store
        self._publisher = publisher
        self._batch_size = batch_size
        self._poll_interval_seconds = poll_interval_seconds
        self._retry_base_seconds = retry_base_seconds
        self._lease_seconds = lease_seconds

    async def dispatch_once(self) -> int:
        events = await self._store.claim(self._batch_size, self._lease_seconds)
        published = 0
        for event in events:
            try:
                await self._publisher.publish(event)
                await self._store.mark_published(event.event_id)
                published += 1
                logger.info(
                    "domain_event_published",
                    extra={
                        "event": "domain_event_published",
                        "event_id": str(event.event_id),
                        "event_type": event.event_type,
                        "aggregate_id": str(event.aggregate_id),
                        "correlation_id": event.correlation_id,
                    },
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                delay = min(self._retry_base_seconds * 2, 60.0)
                await self._store.release_for_retry(event.event_id, delay, "kafka_publish_failed")
                logger.warning(
                    "domain_event_publish_deferred",
                    extra={
                        "event": "domain_event_publish_deferred",
                        "event_id": str(event.event_id),
                        "event_type": event.event_type,
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
                logger.exception("outbox_poll_failed", extra={"event": "outbox_poll_failed"})
            await asyncio.sleep(self._poll_interval_seconds)

    async def close(self) -> None:
        await self._publisher.close()
