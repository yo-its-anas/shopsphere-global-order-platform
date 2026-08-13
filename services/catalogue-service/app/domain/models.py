"""Persistence-independent Product Catalogue domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


class InventoryMovementType(str, Enum):
    INITIAL_STOCK = "INITIAL_STOCK"
    STOCK_RECEIPT = "STOCK_RECEIPT"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    DAMAGE = "DAMAGE"
    CORRECTION = "CORRECTION"
    # Reserved for the future Order Processing integration. No current API can issue these.
    RESERVATION = "RESERVATION"
    RELEASE = "RELEASE"
    FULFILMENT = "FULFILMENT"


class AvailabilityState(str, Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"


@dataclass(slots=True)
class ProductCategory:
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True
    parent_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    category_id: UUID
    description: str | None = None
    status: ProductStatus = ProductStatus.DRAFT
    is_searchable: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class ProductPrice:
    product_id: UUID
    amount: Decimal
    currency_code: str
    is_active: bool = True
    effective_from: datetime = field(default_factory=utc_now)
    effective_to: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class InventoryItem:
    product_id: UUID
    quantity_on_hand: int
    quantity_reserved: int = 0
    reorder_threshold: int = 0
    location_code: str = "PRIMARY"
    version: int = 1
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def quantity_available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved

    @property
    def availability_state(self) -> AvailabilityState:
        if self.quantity_available == 0:
            return AvailabilityState.OUT_OF_STOCK
        if self.quantity_available <= self.reorder_threshold:
            return AvailabilityState.LOW_STOCK
        return AvailabilityState.IN_STOCK


@dataclass(frozen=True, slots=True)
class InventoryMovement:
    inventory_item_id: UUID
    product_id: UUID
    movement_type: InventoryMovementType
    quantity_delta: int
    previous_quantity_on_hand: int
    resulting_quantity_on_hand: int
    previous_quantity_reserved: int
    resulting_quantity_reserved: int
    actor_subject: str
    correlation_id: str
    idempotency_key: str
    reason: str
    reference: str | None = None
    reserved_delta: int = 0
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utc_now)
