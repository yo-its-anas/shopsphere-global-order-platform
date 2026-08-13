"""Persistence-independent shopping-cart domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CartStatus(str, Enum):
    ACTIVE = "active"


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
