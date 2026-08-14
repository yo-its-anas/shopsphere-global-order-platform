"""Validated API contracts for inventory management."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.domain.inventory import CURRENT_STOCK_MOVEMENT_TYPES
from app.domain.models import AvailabilityState, InventoryMovementType, InventoryReservationStatus

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
Reference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
IdempotencyKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
ExternalReference = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InventoryInitialize(StrictModel):
    quantity_on_hand: int = Field(ge=0, le=2_147_483_647)
    reorder_threshold: int = Field(default=0, ge=0, le=2_147_483_647)
    reason: Reason
    reference: Reference | None = None
    idempotency_key: IdempotencyKey


class InventoryAdjustment(StrictModel):
    movement_type: InventoryMovementType
    quantity_delta: int = Field(ge=-2_147_483_647, le=2_147_483_647)
    reason: Reason
    reference: Reference | None = None
    idempotency_key: IdempotencyKey
    expected_version: int | None = Field(default=None, ge=1)

    @field_validator("movement_type")
    @classmethod
    def permit_current_stock_types(cls, value: InventoryMovementType) -> InventoryMovementType:
        if value not in CURRENT_STOCK_MOVEMENT_TYPES:
            raise ValueError("Movement type is reserved for a future capability")
        return value


class InventorySettingsUpdate(StrictModel):
    reorder_threshold: int = Field(ge=0, le=2_147_483_647)
    expected_version: int | None = Field(default=None, ge=1)


class AvailabilityResponse(StrictModel):
    product_id: UUID
    quantity_available: int
    state: AvailabilityState
    as_of: datetime


class InventoryItemResponse(StrictModel):
    id: UUID
    product_id: UUID
    location_code: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    reorder_threshold: int
    state: AvailabilityState
    version: int
    created_at: datetime
    updated_at: datetime


class InventoryItemListResponse(StrictModel):
    items: list[InventoryItemResponse]
    offset: int
    limit: int
    total: int


class InventoryMovementResponse(StrictModel):
    id: UUID
    inventory_item_id: UUID
    product_id: UUID
    movement_type: InventoryMovementType
    quantity_delta: int
    reserved_delta: int
    previous_quantity_on_hand: int
    resulting_quantity_on_hand: int
    previous_quantity_reserved: int
    resulting_quantity_reserved: int
    reason: str
    reference: str | None
    actor_subject: str
    correlation_id: str
    idempotency_key: str
    occurred_at: datetime


class InventoryMovementListResponse(StrictModel):
    items: list[InventoryMovementResponse]
    offset: int
    limit: int
    total: int


class InventoryMutationResponse(StrictModel):
    inventory: InventoryItemResponse
    movement: InventoryMovementResponse


class InventoryReservationCreate(StrictModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=2_147_483_647)
    external_reference: ExternalReference
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def require_future_expiry(self) -> InventoryReservationCreate:
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None:
                raise ValueError("expires_at must include a timezone")
            if self.expires_at <= datetime.now(self.expires_at.tzinfo):
                raise ValueError("expires_at must be in the future")
        return self


class InventoryReservationResponse(StrictModel):
    reservation_id: UUID
    product_id: UUID
    quantity: int
    external_reference: str
    status: InventoryReservationStatus
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InventoryReservationMutationResponse(StrictModel):
    reservation: InventoryReservationResponse
    inventory: InventoryItemResponse
    movement: InventoryMovementResponse


class InventoryStatisticsResponse(StrictModel):
    location_code: str
    total_products_tracked: int
    in_stock_products: int
    low_stock_products: int
    out_of_stock_products: int
    total_units_on_hand: int
    reserved_units: int
    available_units: int
    calculated_at: datetime
