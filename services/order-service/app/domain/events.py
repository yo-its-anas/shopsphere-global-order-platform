"""Versioned, non-sensitive order event contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.domain.models import Order, utc_now

ORDER_CREATED = "order.created.v1"
ORDER_CONFIRMED = "order.confirmed.v1"
ORDER_STATUS_CHANGED = "order.status_changed.v1"
ORDER_CANCELLED = "order.cancelled.v1"
EVENT_VERSION = 1
PRODUCER = "order-service"


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Stable event envelope persisted to the outbox and sent unchanged to Kafka."""

    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    correlation_id: str
    payload: dict[str, Any]
    event_id: UUID = field(default_factory=uuid4)
    event_version: int = EVENT_VERSION
    occurred_at: datetime = field(default_factory=utc_now)
    producer: str = PRODUCER

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": str(self.aggregate_id),
            "occurred_at": _utc_text(self.occurred_at),
            "correlation_id": self.correlation_id,
            "producer": self.producer,
            "payload": self.payload,
        }


def order_created(order: Order, item_count: int, correlation_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=ORDER_CREATED,
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=correlation_id,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status.value,
            "currency_code": order.currency_code,
            "total": format(order.total, "f"),
            "item_count": item_count,
        },
    )


def order_confirmed(order: Order, correlation_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=ORDER_CONFIRMED,
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=correlation_id,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status.value,
            "currency_code": order.currency_code,
            "total": format(order.total, "f"),
        },
    )


def order_status_changed(order: Order, previous_status: str, correlation_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=ORDER_STATUS_CHANGED,
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=correlation_id,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "previous_status": previous_status,
            "status": order.status.value,
        },
    )


def order_cancelled(order: Order, correlation_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=ORDER_CANCELLED,
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=correlation_id,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status.value,
        },
    )
