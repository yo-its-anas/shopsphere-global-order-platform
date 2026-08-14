"""Versioned, non-sensitive catalogue and inventory domain-event contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.domain.models import (
    InventoryItem,
    InventoryMovement,
    InventoryReservation,
    Product,
    ProductPrice,
    utc_now,
)

PRODUCT_CREATED = "catalogue.product.created.v1"
PRODUCT_UPDATED = "catalogue.product.updated.v1"
PRICE_CHANGED = "catalogue.price.changed.v1"
INVENTORY_ADJUSTED = "inventory.adjusted.v1"
INVENTORY_LOW = "inventory.low.v1"
INVENTORY_OUT_OF_STOCK = "inventory.out-of-stock.v1"
INVENTORY_RESERVED = "inventory.reserved.v1"
INVENTORY_RESERVATION_RELEASED = "inventory.reservation_released.v1"
INVENTORY_RESERVATION_CONSUMED = "inventory.reservation_consumed.v1"
EVENT_VERSION = 1
PRODUCER = "catalogue-service"


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


def product_created(product: Product, correlation_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=PRODUCT_CREATED,
        aggregate_type="product",
        aggregate_id=product.id,
        correlation_id=correlation_id,
        payload={
            "product_id": str(product.id),
            "sku": product.sku,
            "category_id": str(product.category_id),
            "status": product.status.value,
            "is_searchable": product.is_searchable,
        },
    )


def product_updated(product: Product, changed_fields: set[str], correlation_id: str) -> DomainEvent:
    allowed_fields = {
        "name",
        "description",
        "category_id",
        "status",
        "is_searchable",
    }
    return DomainEvent(
        event_type=PRODUCT_UPDATED,
        aggregate_type="product",
        aggregate_id=product.id,
        correlation_id=correlation_id,
        payload={
            "product_id": str(product.id),
            "sku": product.sku,
            "changed_fields": sorted(changed_fields & allowed_fields),
            "status": product.status.value,
            "is_searchable": product.is_searchable,
        },
    )


def price_changed(price: ProductPrice, correlation_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=PRICE_CHANGED,
        aggregate_type="product",
        aggregate_id=price.product_id,
        correlation_id=correlation_id,
        payload={
            "product_id": str(price.product_id),
            "price_id": str(price.id),
            "amount": format(Decimal(price.amount), "f"),
            "currency_code": price.currency_code,
            "effective_from": _utc_text(price.effective_from),
        },
    )


def inventory_adjusted(
    item: InventoryItem, movement: InventoryMovement, correlation_id: str
) -> DomainEvent:
    return DomainEvent(
        event_type=INVENTORY_ADJUSTED,
        aggregate_type="inventory_item",
        aggregate_id=item.id,
        correlation_id=correlation_id,
        payload={
            "inventory_item_id": str(item.id),
            "product_id": str(item.product_id),
            "movement_id": str(movement.id),
            "movement_type": movement.movement_type.value,
            "quantity_delta": movement.quantity_delta,
            "quantity_on_hand": item.quantity_on_hand,
            "quantity_reserved": item.quantity_reserved,
            "quantity_available": item.quantity_available,
            "location_code": item.location_code,
            "version": item.version,
        },
    )


def inventory_threshold_event(item: InventoryItem, correlation_id: str) -> DomainEvent | None:
    if item.quantity_available == 0:
        event_type = INVENTORY_OUT_OF_STOCK
    elif item.quantity_available <= item.reorder_threshold:
        event_type = INVENTORY_LOW
    else:
        return None
    return DomainEvent(
        event_type=event_type,
        aggregate_type="inventory_item",
        aggregate_id=item.id,
        correlation_id=correlation_id,
        payload={
            "inventory_item_id": str(item.id),
            "product_id": str(item.product_id),
            "quantity_available": item.quantity_available,
            "reorder_threshold": item.reorder_threshold,
            "location_code": item.location_code,
        },
    )


def inventory_reservation_event(
    event_type: str,
    item: InventoryItem,
    reservation: InventoryReservation,
    movement: InventoryMovement,
    correlation_id: str,
) -> DomainEvent:
    """Build a safe reservation lifecycle event without workflow payload leakage."""

    if event_type not in {
        INVENTORY_RESERVED,
        INVENTORY_RESERVATION_RELEASED,
        INVENTORY_RESERVATION_CONSUMED,
    }:
        raise ValueError("Unsupported inventory reservation event type")
    return DomainEvent(
        event_type=event_type,
        aggregate_type="inventory_reservation",
        aggregate_id=reservation.id,
        correlation_id=correlation_id,
        payload={
            "reservation_id": str(reservation.id),
            "inventory_item_id": str(item.id),
            "product_id": str(item.product_id),
            "movement_id": str(movement.id),
            "quantity": reservation.quantity,
            "status": reservation.status.value,
            "quantity_on_hand": item.quantity_on_hand,
            "quantity_reserved": item.quantity_reserved,
            "quantity_available": item.quantity_available,
            "location_code": item.location_code,
            "version": item.version,
        },
    )
