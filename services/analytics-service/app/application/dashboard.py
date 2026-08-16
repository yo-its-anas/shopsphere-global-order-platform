"""Resilient read-only composition of source-owned executive aggregates."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from datetime import datetime, timezone
from typing import TypeVar, cast

from app.core.metrics import AnalyticsMetrics
from app.domain.models import (
    CustomerKpis,
    DataStatus,
    DependencyState,
    InventoryKpis,
    OperationalAlert,
    OrderKpis,
    SourceResult,
)
from app.infrastructure.service_clients import DashboardSources, SourceError
from app.schemas.dashboard import (
    AlertResponse,
    AlertsResponse,
    CustomerKpiResponse,
    DashboardMetadata,
    DependencyStatusResponse,
    ExecutiveSummaryResponse,
    InventoryKpiResponse,
    OperationsResponse,
    OrderKpiResponse,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", CustomerKpis, InventoryKpis, OrderKpis)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _data_status(results: list[SourceResult]) -> DataStatus:
    available = sum(result.available for result in results)
    if available == len(results):
        return DataStatus.COMPLETE
    if available == 0:
        return DataStatus.UNAVAILABLE
    return DataStatus.PARTIAL


def _metadata(results: list[SourceResult]) -> DashboardMetadata:
    return DashboardMetadata(
        generated_at=_utc_now(),
        data_status=_data_status(results),
        dependency_status=[
            DependencyStatusResponse(service=result.service, status=result.state)
            for result in results
        ],
    )


class DashboardService:
    """Compose safe KPI views without becoming a transactional data owner."""

    def __init__(self, sources: DashboardSources, metrics: AnalyticsMetrics) -> None:
        self._sources = sources
        self._metrics = metrics

    async def _capture(self, service: str, operation: Awaitable[T]) -> SourceResult:
        try:
            value = await operation
        except SourceError as exc:
            self._metrics.observe_dependency(service, exc.state.value)
            logger.warning(
                "analytics_dependency_unavailable",
                extra={
                    "event": "analytics_dependency_unavailable",
                    "upstream_service": service,
                    "result": exc.state.value,
                },
            )
            return SourceResult(service, None, exc.state)
        except Exception:
            self._metrics.observe_dependency(service, DependencyState.INVALID_RESPONSE.value)
            logger.warning(
                "analytics_dependency_invalid_response",
                extra={
                    "event": "analytics_dependency_invalid_response",
                    "upstream_service": service,
                    "result": DependencyState.INVALID_RESPONSE.value,
                },
            )
            return SourceResult(service, None, DependencyState.INVALID_RESPONSE)
        self._metrics.observe_dependency(service, DependencyState.AVAILABLE.value)
        return SourceResult(service, value, DependencyState.AVAILABLE)

    def _record(self, endpoint: str, metadata: DashboardMetadata) -> None:
        self._metrics.observe_aggregation(endpoint, metadata.data_status.value)

    async def orders(self, access_token: str, correlation_id: str) -> OrderKpiResponse:
        result = await self._capture(
            "order-service", self._sources.orders(access_token, correlation_id)
        )
        metadata = _metadata([result])
        values = cast(OrderKpis | None, result.value)
        response = OrderKpiResponse(
            metadata=metadata,
            total_orders=values.total_orders if values else None,
            total_revenue_simulated=values.total_revenue_simulated if values else None,
            revenue_currency=values.revenue_currency if values else None,
            simulated_revenue_by_currency=(
                values.simulated_revenue_by_currency if values else None
            ),
            confirmed_orders=values.confirmed_orders if values else None,
            processing_orders=values.processing_orders if values else None,
            fulfilled_orders=values.fulfilled_orders if values else None,
            cancelled_orders=values.cancelled_orders if values else None,
            failed_orders=values.failed_orders if values else None,
            fulfilment_rate=values.fulfilment_rate if values else None,
        )
        self._record("orders", metadata)
        return response

    async def inventory(self, access_token: str, correlation_id: str) -> InventoryKpiResponse:
        result = await self._capture(
            "catalogue-service", self._sources.inventory(access_token, correlation_id)
        )
        metadata = _metadata([result])
        values = cast(InventoryKpis | None, result.value)
        response = InventoryKpiResponse(
            metadata=metadata,
            product_count=values.product_count if values else None,
            available_product_count=values.available_product_count if values else None,
            total_products_tracked=values.total_products_tracked if values else None,
            in_stock_count=values.in_stock_count if values else None,
            low_stock_count=values.low_stock_count if values else None,
            out_of_stock_count=values.out_of_stock_count if values else None,
            total_units_on_hand=values.total_units_on_hand if values else None,
            reserved_units=values.reserved_units if values else None,
            available_units=values.available_units if values else None,
            inventory_calculated_at=values.calculated_at if values else None,
        )
        self._record("inventory", metadata)
        return response

    async def customers(self, access_token: str, correlation_id: str) -> CustomerKpiResponse:
        result = await self._capture(
            "customer-service", self._sources.customers(access_token, correlation_id)
        )
        metadata = _metadata([result])
        values = cast(CustomerKpis | None, result.value)
        response = CustomerKpiResponse(
            metadata=metadata,
            customer_count=values.customer_count if values else None,
        )
        self._record("customers", metadata)
        return response

    async def summary(self, access_token: str, correlation_id: str) -> ExecutiveSummaryResponse:
        customer_result, inventory_result, order_result = await asyncio.gather(
            self._capture(
                "customer-service", self._sources.customers(access_token, correlation_id)
            ),
            self._capture(
                "catalogue-service", self._sources.inventory(access_token, correlation_id)
            ),
            self._capture("order-service", self._sources.orders(access_token, correlation_id)),
        )
        results = [customer_result, inventory_result, order_result]
        metadata = _metadata(results)
        customer = cast(CustomerKpis | None, customer_result.value)
        inventory = cast(InventoryKpis | None, inventory_result.value)
        orders = cast(OrderKpis | None, order_result.value)
        response = ExecutiveSummaryResponse(
            metadata=metadata,
            total_orders=orders.total_orders if orders else None,
            total_revenue_simulated=orders.total_revenue_simulated if orders else None,
            revenue_currency=orders.revenue_currency if orders else None,
            simulated_revenue_by_currency=(
                orders.simulated_revenue_by_currency if orders else None
            ),
            customer_count=customer.customer_count if customer else None,
            product_count=inventory.product_count if inventory else None,
            available_product_count=(inventory.available_product_count if inventory else None),
            low_stock_count=inventory.low_stock_count if inventory else None,
            out_of_stock_count=inventory.out_of_stock_count if inventory else None,
            fulfilled_orders=orders.fulfilled_orders if orders else None,
            processing_orders=orders.processing_orders if orders else None,
            cancelled_orders=orders.cancelled_orders if orders else None,
            fulfilment_rate=orders.fulfilment_rate if orders else None,
        )
        self._record("summary", metadata)
        return response

    async def operations(self, correlation_id: str) -> OperationsResponse:
        results = await self._sources.health(correlation_id)
        for result in results:
            self._metrics.observe_dependency(result.service, result.state.value)
        metadata = _metadata(results)
        response = OperationsResponse(
            metadata=metadata,
            healthy_dependencies=sum(result.available for result in results),
        )
        self._record("operations", metadata)
        return response

    async def alerts(self, access_token: str, correlation_id: str) -> AlertsResponse:
        health_results, inventory_result = await asyncio.gather(
            self._sources.health(correlation_id),
            self._capture(
                "catalogue-service", self._sources.inventory(access_token, correlation_id)
            ),
        )
        for result in health_results:
            self._metrics.observe_dependency(result.service, result.state.value)
        status_by_service = {result.service: result for result in health_results}
        status_by_service["catalogue-service"] = (
            inventory_result
            if not inventory_result.available
            else status_by_service.get("catalogue-service", inventory_result)
        )
        results = list(status_by_service.values())
        alerts: list[OperationalAlert] = []
        for result in results:
            if not result.available:
                alerts.append(
                    OperationalAlert(
                        code="dependency_unavailable",
                        severity="critical",
                        source=result.service,
                        message=f"{result.service} is unavailable to executive analytics.",
                    )
                )
        inventory = cast(InventoryKpis | None, inventory_result.value)
        if inventory is not None and inventory.out_of_stock_count:
            alerts.append(
                OperationalAlert(
                    code="inventory_out_of_stock",
                    severity="critical",
                    source="catalogue-service",
                    message=(f"{inventory.out_of_stock_count} tracked products are out of stock."),
                )
            )
        if inventory is not None and inventory.low_stock_count:
            alerts.append(
                OperationalAlert(
                    code="inventory_low_stock",
                    severity="warning",
                    source="catalogue-service",
                    message=f"{inventory.low_stock_count} tracked products have low stock.",
                )
            )
        metadata = _metadata(results)
        response = AlertsResponse(
            metadata=metadata,
            items=[
                AlertResponse(
                    code=alert.code,
                    severity=alert.severity,
                    source=alert.source,
                    message=alert.message,
                )
                for alert in alerts
            ],
        )
        self._record("alerts", metadata)
        return response
