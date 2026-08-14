"""Strict executive dashboard response contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import DataStatus, DependencyState


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DependencyStatusResponse(StrictModel):
    service: Literal["customer-service", "catalogue-service", "order-service"]
    status: DependencyState


class DashboardMetadata(StrictModel):
    generated_at: datetime
    data_status: DataStatus
    dependency_status: list[DependencyStatusResponse]


class OrderKpiResponse(StrictModel):
    metadata: DashboardMetadata
    total_orders: int | None
    total_revenue_simulated: Decimal | None
    revenue_currency: str | None
    simulated_revenue_by_currency: dict[str, Decimal] | None
    revenue_label: str = "Simulated order value; payment settlement is not implemented."
    revenue_included_statuses: tuple[str, ...] = ("CONFIRMED", "PROCESSING", "FULFILLED")
    confirmed_orders: int | None
    processing_orders: int | None
    fulfilled_orders: int | None
    cancelled_orders: int | None
    failed_orders: int | None
    fulfilment_rate: Decimal | None


class InventoryKpiResponse(StrictModel):
    metadata: DashboardMetadata
    product_count: int | None
    available_product_count: int | None
    total_products_tracked: int | None
    in_stock_count: int | None
    low_stock_count: int | None
    out_of_stock_count: int | None
    total_units_on_hand: int | None
    reserved_units: int | None
    available_units: int | None
    inventory_calculated_at: datetime | None


class CustomerKpiResponse(StrictModel):
    metadata: DashboardMetadata
    customer_count: int | None
    customer_count_definition: str = "Provisioned ShopSphere customer business profiles."


class ExecutiveSummaryResponse(StrictModel):
    metadata: DashboardMetadata
    total_orders: int | None
    total_revenue_simulated: Decimal | None
    revenue_currency: str | None
    simulated_revenue_by_currency: dict[str, Decimal] | None
    customer_count: int | None
    product_count: int | None
    available_product_count: int | None
    low_stock_count: int | None
    out_of_stock_count: int | None
    fulfilled_orders: int | None
    processing_orders: int | None
    cancelled_orders: int | None
    fulfilment_rate: Decimal | None
    revenue_label: str = "Simulated order value; payment settlement is not implemented."


class OperationsResponse(StrictModel):
    metadata: DashboardMetadata
    healthy_dependencies: int
    total_dependencies: int = 3


class AlertResponse(StrictModel):
    code: str = Field(min_length=1, max_length=80)
    severity: Literal["informational", "warning", "critical"]
    source: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=240)


class AlertsResponse(StrictModel):
    metadata: DashboardMetadata
    items: list[AlertResponse]
