"""Checkout confirmation API contracts."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrderItemResponse(StrictModel):
    product_id: UUID
    sku: str
    product_name: str
    quantity: int
    unit_price: Decimal
    currency_code: str
    line_total: Decimal


class OrderConfirmationResponse(StrictModel):
    order_id: UUID
    order_number: str
    status: str
    items: list[OrderItemResponse]
    currency_code: str
    subtotal: Decimal
    total: Decimal
    created_at: datetime
    payment_status: str = "not_in_scope"
