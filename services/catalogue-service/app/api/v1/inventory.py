"""Versioned enterprise inventory API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.dependencies import (
    get_cache,
    get_inventory_reservation_service,
    get_inventory_service,
    require_roles,
)
from app.application.cache import CacheBackend, cache_scope, get_cached_model, set_cached_model
from app.application.inventory import DEFAULT_LOCATION, InventoryService
from app.application.reservations import InventoryReservationService
from app.core.security import Principal, Role
from app.domain.models import (
    AvailabilityState,
    InventoryItem,
    InventoryMovement,
    InventoryReservation,
    utc_now,
)
from app.schemas.inventory import (
    AvailabilityResponse,
    InventoryAdjustment,
    InventoryInitialize,
    InventoryItemListResponse,
    InventoryItemResponse,
    InventoryMovementListResponse,
    InventoryMovementResponse,
    InventoryMutationResponse,
    InventoryReservationCreate,
    InventoryReservationMutationResponse,
    InventoryReservationResponse,
    InventorySettingsUpdate,
    InventoryStatisticsResponse,
)

router = APIRouter(prefix="/inventory")
availability_reader = require_roles(Role.CUSTOMER, Role.SUPPORT, Role.OPERATIONS_ADMIN)
inventory_reader = require_roles(Role.SUPPORT, Role.OPERATIONS_ADMIN)
inventory_writer = require_roles(Role.OPERATIONS_ADMIN)
reservation_operator = require_roles(Role.ORDER_SERVICE, Role.OPERATIONS_ADMIN)
AvailabilityReader = Annotated[Principal, Depends(availability_reader)]
InventoryReader = Annotated[Principal, Depends(inventory_reader)]
InventoryWriter = Annotated[Principal, Depends(inventory_writer)]
ReservationOperator = Annotated[Principal, Depends(reservation_operator)]
InventoryApplication = Annotated[InventoryService, Depends(get_inventory_service)]
ReservationApplication = Annotated[
    InventoryReservationService, Depends(get_inventory_reservation_service)
]
Cache = Annotated[CacheBackend, Depends(get_cache)]


def _request_id(request: Request) -> str:
    return str(request.state.correlation_id)


def _item_response(item: InventoryItem) -> InventoryItemResponse:
    return InventoryItemResponse(
        id=item.id,
        product_id=item.product_id,
        location_code=item.location_code,
        quantity_on_hand=item.quantity_on_hand,
        quantity_reserved=item.quantity_reserved,
        quantity_available=item.quantity_available,
        reorder_threshold=item.reorder_threshold,
        state=item.availability_state,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _movement_response(movement: InventoryMovement) -> InventoryMovementResponse:
    return InventoryMovementResponse(
        id=movement.id,
        inventory_item_id=movement.inventory_item_id,
        product_id=movement.product_id,
        movement_type=movement.movement_type,
        quantity_delta=movement.quantity_delta,
        reserved_delta=movement.reserved_delta,
        previous_quantity_on_hand=movement.previous_quantity_on_hand,
        resulting_quantity_on_hand=movement.resulting_quantity_on_hand,
        previous_quantity_reserved=movement.previous_quantity_reserved,
        resulting_quantity_reserved=movement.resulting_quantity_reserved,
        reason=movement.reason,
        reference=movement.reference,
        actor_subject=movement.actor_subject,
        correlation_id=movement.correlation_id,
        idempotency_key=movement.idempotency_key,
        occurred_at=movement.occurred_at,
    )


def _reservation_response(reservation: InventoryReservation) -> InventoryReservationResponse:
    return InventoryReservationResponse(
        reservation_id=reservation.id,
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        external_reference=reservation.external_reference,
        status=reservation.status,
        expires_at=reservation.expires_at,
        created_at=reservation.created_at,
        updated_at=reservation.updated_at,
    )


def _reservation_mutation_response(
    reservation: InventoryReservation,
    item: InventoryItem,
    movement: InventoryMovement,
) -> InventoryReservationMutationResponse:
    return InventoryReservationMutationResponse(
        reservation=_reservation_response(reservation),
        inventory=_item_response(item),
        movement=_movement_response(movement),
    )


async def _invalidate_inventory_reads(
    request: Request, cache: CacheBackend, product_id: UUID
) -> None:
    keys = request.app.state.cache_keys
    await cache.delete_prefix(keys.family_prefix("availability"), family="availability")
    await cache.delete(keys.inventory_item(product_id), family="inventory-item")
    await cache.delete_prefix(keys.family_prefix("inventory-list"), family="inventory-list")
    await cache.delete(keys.inventory_statistics, family="inventory-statistics")


@router.post(
    "/reservations",
    response_model=InventoryReservationMutationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Internal inventory reservations"],
    summary="Atomically reserve available inventory",
)
async def reserve_inventory(
    payload: InventoryReservationCreate,
    request: Request,
    actor: ReservationOperator,
    service: ReservationApplication,
    cache: Cache,
) -> InventoryReservationMutationResponse:
    request.app.state.metrics.reservation_started()
    try:
        reservation, item, movement = await service.reserve(
            actor,
            payload.product_id,
            payload.quantity,
            payload.external_reference,
            _request_id(request),
            payload.expires_at,
        )
    except Exception:
        request.app.state.metrics.observe_reservation("failure")
        raise
    request.app.state.metrics.observe_reservation("success")
    await _invalidate_inventory_reads(request, cache, payload.product_id)
    return _reservation_mutation_response(reservation, item, movement)


@router.get(
    "/reservations/{reservation_id}",
    response_model=InventoryReservationResponse,
    tags=["Internal inventory reservations"],
    summary="Retrieve a reservation for retry or reconciliation",
)
async def get_inventory_reservation(
    reservation_id: UUID,
    _: ReservationOperator,
    service: ReservationApplication,
) -> InventoryReservationResponse:
    return _reservation_response(await service.get(reservation_id))


@router.post(
    "/reservations/{reservation_id}/release",
    response_model=InventoryReservationMutationResponse,
    tags=["Internal inventory reservations"],
    summary="Idempotently release an active reservation",
)
async def release_inventory_reservation(
    reservation_id: UUID,
    request: Request,
    actor: ReservationOperator,
    service: ReservationApplication,
    cache: Cache,
) -> InventoryReservationMutationResponse:
    reservation, item, movement = await service.release(actor, reservation_id, _request_id(request))
    await _invalidate_inventory_reads(request, cache, reservation.product_id)
    return _reservation_mutation_response(reservation, item, movement)


@router.post(
    "/reservations/{reservation_id}/consume",
    response_model=InventoryReservationMutationResponse,
    tags=["Internal inventory reservations"],
    summary="Consume reserved allocation without claiming warehouse shipment",
)
async def consume_inventory_reservation(
    reservation_id: UUID,
    request: Request,
    actor: ReservationOperator,
    service: ReservationApplication,
    cache: Cache,
) -> InventoryReservationMutationResponse:
    reservation, item, movement = await service.consume(actor, reservation_id, _request_id(request))
    await _invalidate_inventory_reads(request, cache, reservation.product_id)
    return _reservation_mutation_response(reservation, item, movement)


@router.get(
    "/products/{product_id}/availability",
    response_model=AvailabilityResponse,
    tags=["Inventory availability"],
    summary="Retrieve safe product availability",
)
async def get_availability(
    product_id: UUID,
    request: Request,
    actor: AvailabilityReader,
    service: InventoryApplication,
    cache: Cache,
) -> AvailabilityResponse:
    key = request.app.state.cache_keys.availability(product_id, cache_scope(actor.roles))
    cached = await get_cached_model(cache, key, "availability", AvailabilityResponse)
    if cached is not None:
        return cached
    item = await service.get_availability(actor, product_id)
    response = AvailabilityResponse(
        product_id=item.product_id,
        quantity_available=item.quantity_available,
        state=item.availability_state,
        as_of=item.updated_at,
    )
    await set_cached_model(
        cache,
        key,
        "availability",
        response,
        request.app.state.settings.availability_cache_ttl_seconds,
    )
    return response


@router.get(
    "/products/{product_id}",
    response_model=InventoryItemResponse,
    tags=["Inventory operations"],
    summary="Retrieve operational inventory balances",
)
async def get_inventory_item(
    product_id: UUID,
    request: Request,
    _: InventoryReader,
    service: InventoryApplication,
    cache: Cache,
) -> InventoryItemResponse:
    key = request.app.state.cache_keys.inventory_item(product_id)
    cached = await get_cached_model(cache, key, "inventory-item", InventoryItemResponse)
    if cached is not None:
        return cached
    response = _item_response(await service.get_item(product_id))
    await set_cached_model(
        cache,
        key,
        "inventory-item",
        response,
        request.app.state.settings.availability_cache_ttl_seconds,
    )
    return response


@router.post(
    "/products/{product_id}/initialize",
    response_model=InventoryMutationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Inventory administration"],
    summary="Initialize inventory for a product",
)
async def initialize_inventory(
    product_id: UUID,
    payload: InventoryInitialize,
    request: Request,
    actor: InventoryWriter,
    service: InventoryApplication,
    cache: Cache,
) -> InventoryMutationResponse:
    item, movement = await service.initialize(
        actor,
        product_id,
        payload.quantity_on_hand,
        payload.reorder_threshold,
        payload.reason,
        payload.reference,
        payload.idempotency_key,
        _request_id(request),
    )
    await _invalidate_inventory_reads(request, cache, product_id)
    return InventoryMutationResponse(
        inventory=_item_response(item), movement=_movement_response(movement)
    )


@router.post(
    "/products/{product_id}/adjustments",
    response_model=InventoryMutationResponse,
    tags=["Inventory administration"],
    summary="Apply an auditable stock adjustment",
)
async def adjust_inventory(
    product_id: UUID,
    payload: InventoryAdjustment,
    request: Request,
    actor: InventoryWriter,
    service: InventoryApplication,
    cache: Cache,
) -> InventoryMutationResponse:
    item, movement = await service.adjust(
        actor,
        product_id,
        payload.movement_type,
        payload.quantity_delta,
        payload.reason,
        payload.reference,
        payload.idempotency_key,
        payload.expected_version,
        _request_id(request),
    )
    await _invalidate_inventory_reads(request, cache, product_id)
    return InventoryMutationResponse(
        inventory=_item_response(item), movement=_movement_response(movement)
    )


@router.patch(
    "/products/{product_id}/settings",
    response_model=InventoryItemResponse,
    tags=["Inventory administration"],
    summary="Update inventory control settings",
)
async def update_inventory_settings(
    product_id: UUID,
    request: Request,
    payload: InventorySettingsUpdate,
    _: InventoryWriter,
    service: InventoryApplication,
    cache: Cache,
) -> InventoryItemResponse:
    response = _item_response(
        await service.update_settings(
            product_id, payload.reorder_threshold, payload.expected_version
        )
    )
    await _invalidate_inventory_reads(request, cache, product_id)
    return response


@router.get(
    "/products/{product_id}/movements",
    response_model=InventoryMovementListResponse,
    tags=["Inventory operations"],
    summary="Retrieve append-only inventory movement history",
)
async def list_inventory_movements(
    product_id: UUID,
    _: InventoryReader,
    service: InventoryApplication,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> InventoryMovementListResponse:
    movements, total = await service.list_movements(product_id, offset, limit)
    return InventoryMovementListResponse(
        items=[_movement_response(movement) for movement in movements],
        offset=offset,
        limit=limit,
        total=total,
    )


@router.get(
    "",
    response_model=InventoryItemListResponse,
    tags=["Inventory operations"],
    summary="List and filter tracked inventory",
)
async def list_inventory(
    request: Request,
    _: InventoryReader,
    service: InventoryApplication,
    cache: Cache,
    inventory_state: Annotated[AvailabilityState | None, Query(alias="state")] = None,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> InventoryItemListResponse:
    key = request.app.state.cache_keys.inventory_list(inventory_state, offset, limit)
    cached = await get_cached_model(cache, key, "inventory-list", InventoryItemListResponse)
    if cached is not None:
        return cached
    items, total = await service.list_items(inventory_state, offset, limit)
    response = InventoryItemListResponse(
        items=[_item_response(item) for item in items],
        offset=offset,
        limit=limit,
        total=total,
    )
    await set_cached_model(
        cache,
        key,
        "inventory-list",
        response,
        request.app.state.settings.availability_cache_ttl_seconds,
    )
    return response


@router.get(
    "/statistics",
    response_model=InventoryStatisticsResponse,
    tags=["Inventory operations"],
    summary="Calculate inventory statistics from persisted balances",
)
async def get_inventory_statistics(
    request: Request,
    _: InventoryReader,
    service: InventoryApplication,
    cache: Cache,
) -> InventoryStatisticsResponse:
    key = request.app.state.cache_keys.inventory_statistics
    cached = await get_cached_model(cache, key, "inventory-statistics", InventoryStatisticsResponse)
    if cached is not None:
        return cached
    values = await service.statistics()
    response = InventoryStatisticsResponse(
        location_code=DEFAULT_LOCATION,
        calculated_at=utc_now(),
        **values,
    )
    await set_cached_model(
        cache,
        key,
        "inventory-statistics",
        response,
        request.app.state.settings.availability_cache_ttl_seconds,
    )
    return response
