"""Inventory aggregate invariants and stock transition semantics."""

from __future__ import annotations

from dataclasses import replace

from app.core.errors import InvalidOperationError
from app.domain.models import InventoryItem, InventoryMovementType, utc_now

CURRENT_STOCK_MOVEMENT_TYPES = frozenset(
    {
        InventoryMovementType.STOCK_RECEIPT,
        InventoryMovementType.MANUAL_ADJUSTMENT,
        InventoryMovementType.DAMAGE,
        InventoryMovementType.CORRECTION,
    }
)


def validate_balances(item: InventoryItem) -> None:
    if (
        item.quantity_on_hand < 0
        or item.quantity_reserved < 0
        or item.quantity_reserved > item.quantity_on_hand
        or item.reorder_threshold < 0
        or item.version < 1
    ):
        raise InvalidOperationError


def apply_stock_delta(
    item: InventoryItem,
    movement_type: InventoryMovementType,
    quantity_delta: int,
) -> InventoryItem:
    if movement_type not in CURRENT_STOCK_MOVEMENT_TYPES or quantity_delta == 0:
        raise InvalidOperationError
    if movement_type is InventoryMovementType.STOCK_RECEIPT and quantity_delta < 1:
        raise InvalidOperationError
    if movement_type is InventoryMovementType.DAMAGE and quantity_delta > -1:
        raise InvalidOperationError

    updated = replace(
        item,
        quantity_on_hand=item.quantity_on_hand + quantity_delta,
        version=item.version + 1,
        updated_at=utc_now(),
    )
    validate_balances(updated)
    return updated
