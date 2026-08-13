"""Persistence-independent shopping-cart domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CartStatus(str, Enum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"


class OrderStatus(str, Enum):
    CONFIRMED = "CONFIRMED"


class CheckoutAttemptStatus(str, Enum):
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    COMPENSATION_REQUIRED = "COMPENSATION_REQUIRED"


@dataclass(slots=True)
class ShoppingCart:
    customer_identity_subject: str
    currency_code: str
    id: UUID = field(default_factory=uuid4)
    status: CartStatus = CartStatus.ACTIVE
    version: int = 1
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class CartItem:
    cart_id: UUID
    product_id: UUID
    quantity: int
    display_sku: str
    display_name: str
    display_unit_price: Decimal
    display_currency_code: str
    display_quantity_available: int | None
    snapshot_at: datetime
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def display_line_subtotal(self) -> Decimal:
        return self.display_unit_price * self.quantity


@dataclass(frozen=True, slots=True)
class CatalogueProductSnapshot:
    product_id: UUID
    sku: str
    name: str
    status: str
    is_searchable: bool
    unit_price: Decimal
    currency_code: str
    quantity_available: int | None
    captured_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class InventoryReservationReceipt:
    reservation_id: UUID
    product_id: UUID
    quantity: int
    external_reference: str
    status: str


@dataclass(slots=True)
class Order:
    customer_identity_subject: str
    source_cart_id: UUID
    order_number: str
    currency_code: str
    subtotal: Decimal
    total: Decimal
    id: UUID = field(default_factory=uuid4)
    status: OrderStatus = OrderStatus.CONFIRMED
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class OrderItem:
    order_id: UUID
    product_id: UUID
    sku: str
    product_name: str
    quantity: int
    unit_price: Decimal
    currency_code: str
    line_total: Decimal
    reservation_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class OrderStatusHistory:
    order_id: UUID
    status: OrderStatus
    actor_subject: str
    correlation_id: str
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class OrderAuditEvent:
    order_id: UUID
    action: str
    actor_subject: str
    correlation_id: str
    metadata: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class CheckoutAttempt:
    customer_identity_subject: str
    idempotency_key: str
    source_cart_id: UUID
    source_cart_version: int
    request_fingerprint: str
    reservation_plan: list[dict[str, Any]]
    id: UUID = field(default_factory=uuid4)
    status: CheckoutAttemptStatus = CheckoutAttemptStatus.PROCESSING
    order_id: UUID | None = None
    reservation_ids: list[str] = field(default_factory=list)
    unresolved_reservations: list[dict[str, str]] = field(default_factory=list)
    failure_code: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class OrderDomainEvent:
    event_type: str
    aggregate_id: UUID
    correlation_id: str
    payload: dict[str, Any]
    event_id: UUID = field(default_factory=uuid4)
    event_version: int = 1
    aggregate_type: str = "order"
    producer: str = "order-service"
    occurred_at: datetime = field(default_factory=utc_now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": str(self.aggregate_id),
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": self.correlation_id,
            "producer": self.producer,
            "payload": self.payload,
        }
