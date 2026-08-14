"""Validated shopping-cart API contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CartItemCreate(StrictModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=1000)


class CartItemQuantityUpdate(StrictModel):
    quantity: int = Field(ge=1, le=1000)


class CartItemResponse(StrictModel):
    id: UUID
    product_id: UUID
    quantity: int
    display_sku: str
    display_name: str
    display_unit_price: Decimal
    display_currency_code: str
    display_quantity_available: int | None
    display_line_subtotal: Decimal
    snapshot_at: datetime
    created_at: datetime
    updated_at: datetime


class ShoppingCartResponse(StrictModel):
    id: UUID
    status: str
    currency_code: str
    version: int
    items: list[CartItemResponse]
    item_count: int
    display_subtotal: Decimal
    pricing_authoritative: bool = False
    pricing_notice: str = (
        "Display estimate only. Prices and availability must be revalidated at checkout."
    )
    created_at: datetime
    updated_at: datetime
