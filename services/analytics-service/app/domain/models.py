"""Read-only business and dependency aggregate models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class DataStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class DependencyState(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    service: str
    state: DependencyState


@dataclass(frozen=True, slots=True)
class CustomerKpis:
    customer_count: int


@dataclass(frozen=True, slots=True)
class InventoryKpis:
    product_count: int
    total_products_tracked: int
    in_stock_count: int
    low_stock_count: int
    out_of_stock_count: int
    total_units_on_hand: int
    reserved_units: int
    available_units: int
    calculated_at: datetime

    @property
    def available_product_count(self) -> int:
        return self.in_stock_count + self.low_stock_count


@dataclass(frozen=True, slots=True)
class OrderKpis:
    total_orders: int
    simulated_revenue_by_currency: dict[str, Decimal]
    confirmed_orders: int
    processing_orders: int
    fulfilled_orders: int
    cancelled_orders: int
    failed_orders: int
    fulfilment_rate: Decimal

    @property
    def total_revenue_simulated(self) -> Decimal | None:
        if len(self.simulated_revenue_by_currency) == 1:
            return next(iter(self.simulated_revenue_by_currency.values()))
        if not self.simulated_revenue_by_currency:
            return Decimal("0.0000")
        return None

    @property
    def revenue_currency(self) -> str | None:
        if len(self.simulated_revenue_by_currency) == 1:
            return next(iter(self.simulated_revenue_by_currency))
        return None


@dataclass(frozen=True, slots=True)
class OperationalAlert:
    code: str
    severity: str
    source: str
    message: str


@dataclass(frozen=True, slots=True)
class SourceResult:
    service: str
    value: CustomerKpis | InventoryKpis | OrderKpis | bool | None
    state: DependencyState

    @property
    def available(self) -> bool:
        return self.state is DependencyState.AVAILABLE
