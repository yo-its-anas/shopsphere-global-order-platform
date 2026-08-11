"""Inventory use cases with transactional movement recording."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import replace
from uuid import UUID

from app.core.errors import ConflictError, ResourceNotFoundError
from app.core.security import Principal, Role
from app.domain.inventory import apply_stock_delta, validate_balances
from app.domain.models import (
    AvailabilityState,
    InventoryItem,
    InventoryMovement,
    InventoryMovementType,
    ProductStatus,
    utc_now,
)
from app.domain.repositories import UnitOfWork

logger = logging.getLogger(__name__)
UnitOfWorkFactory = Callable[[], UnitOfWork]
DEFAULT_LOCATION = "PRIMARY"


class InventoryService:
    """Coordinates inventory invariants and append-only movement persistence."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    @staticmethod
    def _matching_replay(
        movement: InventoryMovement,
        product_id: UUID,
        movement_type: InventoryMovementType,
        quantity_delta: int,
    ) -> bool:
        return (
            movement.product_id == product_id
            and movement.movement_type is movement_type
            and movement.quantity_delta == quantity_delta
        )

    async def initialize(
        self,
        actor: Principal,
        product_id: UUID,
        quantity_on_hand: int,
        reorder_threshold: int,
        reason: str,
        reference: str | None,
        idempotency_key: str,
        correlation_id: str,
    ) -> tuple[InventoryItem, InventoryMovement]:
        async with self._unit_of_work_factory() as work:
            replay = await work.inventory.get_movement_by_idempotency_key(idempotency_key)
            if replay is not None:
                if not self._matching_replay(
                    replay, product_id, InventoryMovementType.INITIAL_STOCK, quantity_on_hand
                ):
                    raise ConflictError
                item = await work.inventory.get_item(product_id, DEFAULT_LOCATION)
                if item is None:
                    raise ConflictError
                return item, replay
            if await work.catalogue.get_product(product_id) is None:
                raise ResourceNotFoundError
            if await work.inventory.get_item(product_id, DEFAULT_LOCATION, for_update=True):
                raise ConflictError
            item = InventoryItem(
                product_id=product_id,
                location_code=DEFAULT_LOCATION,
                quantity_on_hand=quantity_on_hand,
                reorder_threshold=reorder_threshold,
            )
            validate_balances(item)
            movement = InventoryMovement(
                inventory_item_id=item.id,
                product_id=product_id,
                movement_type=InventoryMovementType.INITIAL_STOCK,
                quantity_delta=quantity_on_hand,
                previous_quantity_on_hand=0,
                resulting_quantity_on_hand=quantity_on_hand,
                previous_quantity_reserved=0,
                resulting_quantity_reserved=0,
                actor_subject=actor.subject,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                reason=reason,
                reference=reference,
            )
            work.inventory.add_item(item)
            work.inventory.add_movement(movement)
            await work.flush()
            await work.commit()
        self._log_adjustment(item, movement)
        return item, movement

    async def adjust(
        self,
        actor: Principal,
        product_id: UUID,
        movement_type: InventoryMovementType,
        quantity_delta: int,
        reason: str,
        reference: str | None,
        idempotency_key: str,
        expected_version: int | None,
        correlation_id: str,
    ) -> tuple[InventoryItem, InventoryMovement]:
        async with self._unit_of_work_factory() as work:
            replay = await work.inventory.get_movement_by_idempotency_key(idempotency_key)
            if replay is not None:
                if not self._matching_replay(replay, product_id, movement_type, quantity_delta):
                    raise ConflictError
                item = await work.inventory.get_item(product_id, DEFAULT_LOCATION)
                if item is None:
                    raise ConflictError
                return item, replay

            current = await work.inventory.get_item(product_id, DEFAULT_LOCATION, for_update=True)
            if current is None:
                raise ResourceNotFoundError
            if expected_version is not None and expected_version != current.version:
                raise ConflictError
            updated = apply_stock_delta(current, movement_type, quantity_delta)
            movement = InventoryMovement(
                inventory_item_id=current.id,
                product_id=product_id,
                movement_type=movement_type,
                quantity_delta=quantity_delta,
                previous_quantity_on_hand=current.quantity_on_hand,
                resulting_quantity_on_hand=updated.quantity_on_hand,
                previous_quantity_reserved=current.quantity_reserved,
                resulting_quantity_reserved=updated.quantity_reserved,
                actor_subject=actor.subject,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                reason=reason,
                reference=reference,
            )
            if not await work.inventory.update_item(updated, current.version):
                raise ConflictError
            work.inventory.add_movement(movement)
            await work.flush()
            await work.commit()
        self._log_adjustment(updated, movement)
        return updated, movement

    async def update_settings(
        self,
        product_id: UUID,
        reorder_threshold: int,
        expected_version: int | None,
    ) -> InventoryItem:
        async with self._unit_of_work_factory() as work:
            current = await work.inventory.get_item(product_id, DEFAULT_LOCATION, for_update=True)
            if current is None:
                raise ResourceNotFoundError
            if expected_version is not None and expected_version != current.version:
                raise ConflictError
            updated = replace(
                current,
                reorder_threshold=reorder_threshold,
                version=current.version + 1,
                updated_at=utc_now(),
            )
            validate_balances(updated)
            if not await work.inventory.update_item(updated, current.version):
                raise ConflictError
            await work.flush()
            await work.commit()
            return updated

    async def get_item(self, product_id: UUID) -> InventoryItem:
        async with self._unit_of_work_factory() as work:
            if await work.catalogue.get_product(product_id) is None:
                raise ResourceNotFoundError
            item = await work.inventory.get_item(product_id, DEFAULT_LOCATION)
            if item is None:
                raise ResourceNotFoundError
            return item

    async def get_availability(self, actor: Principal, product_id: UUID) -> InventoryItem:
        async with self._unit_of_work_factory() as work:
            product = await work.catalogue.get_product(product_id)
            if product is None:
                raise ResourceNotFoundError
            operational_reader = actor.has_any_role(Role.SUPPORT, Role.OPERATIONS_ADMIN)
            if not operational_reader and (
                product.status is not ProductStatus.ACTIVE or not product.is_searchable
            ):
                raise ResourceNotFoundError
            if not operational_reader:
                category = await work.catalogue.get_category(product.category_id)
                if category is None or not category.is_active:
                    raise ResourceNotFoundError
            item = await work.inventory.get_item(product_id, DEFAULT_LOCATION)
            if item is None:
                raise ResourceNotFoundError
            return item

    async def list_items(
        self, state: AvailabilityState | None, offset: int, limit: int
    ) -> tuple[Sequence[InventoryItem], int]:
        async with self._unit_of_work_factory() as work:
            return await work.inventory.list_items(
                state=state,
                location_code=DEFAULT_LOCATION,
                offset=offset,
                limit=limit,
            )

    async def list_movements(
        self, product_id: UUID, offset: int, limit: int
    ) -> tuple[Sequence[InventoryMovement], int]:
        async with self._unit_of_work_factory() as work:
            item = await work.inventory.get_item(product_id, DEFAULT_LOCATION)
            if item is None:
                raise ResourceNotFoundError
            return await work.inventory.list_movements(item.id, offset=offset, limit=limit)

    async def statistics(self) -> dict[str, int]:
        async with self._unit_of_work_factory() as work:
            return await work.inventory.statistics(DEFAULT_LOCATION)

    @staticmethod
    def _log_adjustment(item: InventoryItem, movement: InventoryMovement) -> None:
        logger.info(
            "inventory_adjusted",
            extra={
                "event": "inventory_adjusted",
                "product_id": str(item.product_id),
                "movement_id": str(movement.id),
                "movement_type": movement.movement_type.value,
                "quantity_delta": movement.quantity_delta,
                "resulting_quantity_on_hand": item.quantity_on_hand,
                "actor_subject": movement.actor_subject,
                "correlation_id": movement.correlation_id,
            },
        )
