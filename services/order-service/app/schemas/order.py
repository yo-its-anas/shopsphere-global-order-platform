"""Checkout confirmation API contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
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


class OrderSummaryResponse(StrictModel):
    order_id: UUID
    order_number: str
    status: str
    currency_code: str
    total: Decimal
    created_at: datetime
    updated_at: datetime


class OrderPageResponse(StrictModel):
    items: list[OrderSummaryResponse]
    offset: int
    limit: int
    total: int


class OrderStatusHistoryResponse(StrictModel):
    status: str
    actor_subject: str
    correlation_id: str
    occurred_at: datetime


class OrderHistoryResponse(StrictModel):
    order_id: UUID
    current_status: str
    items: list[OrderStatusHistoryResponse]


class OrderAuditEventResponse(StrictModel):
    action: str
    actor_subject: str
    correlation_id: str
    contextual_information: dict[str, Any]
    occurred_at: datetime


class OrderAuditPageResponse(StrictModel):
    order_id: UUID
    items: list[OrderAuditEventResponse]
    offset: int
    limit: int
    total: int


class AdministrativeStatusTransition(StrictModel):
    target_status: Literal["PROCESSING", "FULFILLED"]
