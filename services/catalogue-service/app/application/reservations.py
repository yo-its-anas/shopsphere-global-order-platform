"""Atomic, idempotent inventory reservation lifecycle operations."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.core.errors import ConflictError, InvalidOperationError, ResourceNotFoundError
from app.core.security import Principal
from app.domain.events import (
    INVENTORY_RESERVATION_CONSUMED,
    INVENTORY_RESERVATION_RELEASED,
    INVENTORY_RESERVED,
    inventory_adjusted,
    inventory_reservation_event,
    inventory_threshold_event,
)
from app.domain.inventory import validate_balances
from app.domain.models import (
    InventoryItem,
    InventoryMovement,
    InventoryMovementType,
    InventoryReservation,
    InventoryReservationStatus,
    ProductStatus,
    utc_now,
)
from app.domain.repositories import UnitOfWork

logger = logging.getLogger(__name__)
UnitOfWorkFactory = Callable[[], UnitOfWork]
DEFAULT_LOCATION = "PRIMARY"


class InventoryReservationService:
    """Own reservation balances; order lifecycle decisions remain outside Catalogue."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def reserve(
        self,
        actor: Principal,
        product_id: UUID,
        quantity: int,
        external_reference: str,
        correlation_id: str,
        expires_at: datetime | None = None,
    ) -> tuple[InventoryReservation, InventoryItem, InventoryMovement]:
        async with self._unit_of_work_factory() as work:
            replay = await work.inventory.get_reservation_by_external_reference(external_reference)
            if replay is not None:
                return await self._reservation_replay(
                    work, replay, product_id, quantity, expires_at
                )

            product = await work.catalogue.get_product(product_id)
            if (
                product is None
                or product.status is not ProductStatus.ACTIVE
                or not product.is_searchable
            ):
                raise ResourceNotFoundError

            current = await work.inventory.get_item(product_id, DEFAULT_LOCATION, for_update=True)
            if current is None:
                raise ResourceNotFoundError

            # Recheck after the product row lock. A concurrent identical request may
            # have committed while this transaction waited for the lock.
            replay = await work.inventory.get_reservation_by_external_reference(external_reference)
            if replay is not None:
                return await self._reservation_replay(
                    work, replay, product_id, quantity, expires_at
                )
            if quantity < 1 or quantity > current.quantity_available:
                raise InvalidOperationError

            updated = replace(
                current,
                quantity_reserved=current.quantity_reserved + quantity,
                version=current.version + 1,
                updated_at=utc_now(),
            )
            validate_balances(updated)
            reservation = InventoryReservation(
                inventory_item_id=current.id,
                product_id=product_id,
                quantity=quantity,
                external_reference=external_reference,
                expires_at=expires_at,
            )
            movement = self._movement(
                reservation,
                current,
                updated,
                InventoryMovementType.RESERVATION,
                0,
                quantity,
                actor.subject,
                correlation_id,
                "Inventory reserved for an external order workflow",
            )
            if not await work.inventory.update_item(updated, current.version):
                raise ConflictError
            work.inventory.add_reservation(reservation)
            work.inventory.add_movement(movement)
            self._add_events(
                work,
                INVENTORY_RESERVED,
                current,
                updated,
                reservation,
                movement,
                correlation_id,
            )
            await work.flush()
            await work.commit()
        self._log("inventory_reserved", actor, reservation, updated, correlation_id)
        return reservation, updated, movement

    async def release(
        self, actor: Principal, reservation_id: UUID, correlation_id: str
    ) -> tuple[InventoryReservation, InventoryItem, InventoryMovement]:
        return await self._transition(
            actor,
            reservation_id,
            InventoryReservationStatus.RELEASED,
            InventoryMovementType.RELEASE,
            INVENTORY_RESERVATION_RELEASED,
            correlation_id,
        )

    async def consume(
        self, actor: Principal, reservation_id: UUID, correlation_id: str
    ) -> tuple[InventoryReservation, InventoryItem, InventoryMovement]:
        """Finalize allocation accounting; this does not claim shipment fulfilment."""

        return await self._transition(
            actor,
            reservation_id,
            InventoryReservationStatus.CONSUMED,
            InventoryMovementType.FULFILMENT,
            INVENTORY_RESERVATION_CONSUMED,
            correlation_id,
        )

    async def get(self, reservation_id: UUID) -> InventoryReservation:
        async with self._unit_of_work_factory() as work:
            reservation = await work.inventory.get_reservation(reservation_id)
            if reservation is None:
                raise ResourceNotFoundError
            return reservation

    async def _transition(
        self,
        actor: Principal,
        reservation_id: UUID,
        target: InventoryReservationStatus,
        movement_type: InventoryMovementType,
        event_type: str,
        correlation_id: str,
    ) -> tuple[InventoryReservation, InventoryItem, InventoryMovement]:
        async with self._unit_of_work_factory() as work:
            known = await work.inventory.get_reservation(reservation_id)
            if known is None:
                raise ResourceNotFoundError
            current = await work.inventory.get_item(
                known.product_id, DEFAULT_LOCATION, for_update=True
            )
            if current is None:
                raise ConflictError
            reservation = await work.inventory.get_reservation(reservation_id, for_update=True)
            if reservation is None:
                raise ResourceNotFoundError
            if reservation.status is target:
                movement = await self._get_transition_movement(work, reservation, movement_type)
                return reservation, current, movement
            if reservation.status is not InventoryReservationStatus.ACTIVE:
                raise ConflictError

            if target is InventoryReservationStatus.RELEASED:
                updated = replace(
                    current,
                    quantity_reserved=current.quantity_reserved - reservation.quantity,
                    version=current.version + 1,
                    updated_at=utc_now(),
                )
                quantity_delta = 0
            else:
                updated = replace(
                    current,
                    quantity_on_hand=current.quantity_on_hand - reservation.quantity,
                    quantity_reserved=current.quantity_reserved - reservation.quantity,
                    version=current.version + 1,
                    updated_at=utc_now(),
                )
                quantity_delta = -reservation.quantity
            validate_balances(updated)
            transitioned = replace(reservation, status=target, updated_at=utc_now())
            movement = self._movement(
                transitioned,
                current,
                updated,
                movement_type,
                quantity_delta,
                -reservation.quantity,
                actor.subject,
                correlation_id,
                (
                    "Inventory reservation released"
                    if target is InventoryReservationStatus.RELEASED
                    else "Reserved inventory allocation consumed"
                ),
            )
            if not await work.inventory.update_item(updated, current.version):
                raise ConflictError
            await work.inventory.update_reservation(transitioned)
            work.inventory.add_movement(movement)
            self._add_events(
                work,
                event_type,
                current,
                updated,
                transitioned,
                movement,
                correlation_id,
            )
            await work.flush()
            await work.commit()
        self._log(
            f"inventory_reservation_{target.value.casefold()}",
            actor,
            transitioned,
            updated,
            correlation_id,
        )
        return transitioned, updated, movement

    @staticmethod
    async def _reservation_replay(
        work: UnitOfWork,
        reservation: InventoryReservation,
        product_id: UUID,
        quantity: int,
        expires_at: datetime | None,
    ) -> tuple[InventoryReservation, InventoryItem, InventoryMovement]:
        if (
            reservation.product_id != product_id
            or reservation.quantity != quantity
            or reservation.expires_at != expires_at
        ):
            raise ConflictError
        item = await work.inventory.get_item(product_id, DEFAULT_LOCATION)
        if item is None:
            raise ConflictError
        movement = await work.inventory.get_movement_by_idempotency_key(
            f"reservation:{reservation.id}:reservation"
        )
        if movement is None:
            raise ConflictError
        return reservation, item, movement

    @staticmethod
    async def _get_transition_movement(
        work: UnitOfWork,
        reservation: InventoryReservation,
        movement_type: InventoryMovementType,
    ) -> InventoryMovement:
        movement = await work.inventory.get_movement_by_idempotency_key(
            f"reservation:{reservation.id}:{movement_type.value.casefold()}"
        )
        if movement is None:
            raise ConflictError
        return movement

    @staticmethod
    def _movement(
        reservation: InventoryReservation,
        previous: InventoryItem,
        resulting: InventoryItem,
        movement_type: InventoryMovementType,
        quantity_delta: int,
        reserved_delta: int,
        actor_subject: str,
        correlation_id: str,
        reason: str,
    ) -> InventoryMovement:
        return InventoryMovement(
            inventory_item_id=previous.id,
            product_id=previous.product_id,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            reserved_delta=reserved_delta,
            previous_quantity_on_hand=previous.quantity_on_hand,
            resulting_quantity_on_hand=resulting.quantity_on_hand,
            previous_quantity_reserved=previous.quantity_reserved,
            resulting_quantity_reserved=resulting.quantity_reserved,
            actor_subject=actor_subject,
            correlation_id=correlation_id,
            idempotency_key=(f"reservation:{reservation.id}:{movement_type.value.casefold()}"),
            reason=reason,
            reference=reservation.external_reference,
        )

    @staticmethod
    def _add_events(
        work: UnitOfWork,
        event_type: str,
        previous: InventoryItem,
        resulting: InventoryItem,
        reservation: InventoryReservation,
        movement: InventoryMovement,
        correlation_id: str,
    ) -> None:
        work.outbox.add(
            inventory_reservation_event(
                event_type, resulting, reservation, movement, correlation_id
            )
        )
        work.outbox.add(inventory_adjusted(resulting, movement, correlation_id))
        if resulting.availability_state is not previous.availability_state:
            threshold = inventory_threshold_event(resulting, correlation_id)
            if threshold is not None:
                work.outbox.add(threshold)

    @staticmethod
    def _log(
        event: str,
        actor: Principal,
        reservation: InventoryReservation,
        item: InventoryItem,
        correlation_id: str,
    ) -> None:
        logger.info(
            event,
            extra={
                "event": event,
                "reservation_id": str(reservation.id),
                "product_id": str(reservation.product_id),
                "reservation_status": reservation.status.value,
                "quantity": reservation.quantity,
                "quantity_available": item.quantity_available,
                "actor_subject": actor.subject,
                "correlation_id": correlation_id,
            },
        )
