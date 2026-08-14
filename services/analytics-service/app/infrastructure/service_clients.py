"""Fixed-origin, read-only clients for ShopSphere domain owner APIs."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

import httpx2
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.domain.models import CustomerKpis, DependencyState, InventoryKpis, OrderKpis, SourceResult

_PAGE_SIZE = 100
_REVENUE_STATUSES = frozenset({"CONFIRMED", "PROCESSING", "FULFILLED"})
_ORDER_STATUSES = frozenset(
    {"PENDING", "CONFIRMED", "PROCESSING", "FULFILLED", "CANCELLED", "FAILED"}
)


class SourceError(Exception):
    state = DependencyState.UNAVAILABLE


class SourceTimeoutError(SourceError):
    state = DependencyState.TIMEOUT


class InvalidSourceResponseError(SourceError):
    state = DependencyState.INVALID_RESPONSE


class StrictUpstreamModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CustomerPage(StrictUpstreamModel):
    items: list[dict[str, Any]]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)


class ProductPage(StrictUpstreamModel):
    items: list[dict[str, Any]]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class InventoryStatistics(StrictUpstreamModel):
    location_code: str
    total_products_tracked: int = Field(ge=0)
    in_stock_products: int = Field(ge=0)
    low_stock_products: int = Field(ge=0)
    out_of_stock_products: int = Field(ge=0)
    total_units_on_hand: int = Field(ge=0)
    reserved_units: int = Field(ge=0)
    available_units: int = Field(ge=0)
    calculated_at: datetime


class OrderSummary(StrictUpstreamModel):
    order_id: str
    order_number: str
    status: str
    currency_code: str = Field(min_length=3, max_length=3)
    total: Decimal = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class OrderPage(StrictUpstreamModel):
    items: list[OrderSummary]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class HealthDocument(StrictUpstreamModel):
    status: str
    service: str
    version: str


class ReadOnlyServiceClient:
    """HTTP client bound to one configured origin; callers supply only fixed paths."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx2.AsyncClient(
            base_url=base_url,
            timeout=httpx2.Timeout(timeout_seconds),
            follow_redirects=False,
            transport=transport,
        )

    async def get_json(
        self,
        path: str,
        correlation_id: str,
        *,
        access_token: str | None = None,
        params: Mapping[str, str | int] | None = None,
    ) -> dict[str, Any]:
        headers = {"X-Request-ID": correlation_id, "Accept": "application/json"}
        if access_token is not None:
            headers["Authorization"] = f"Bearer {access_token}"
        try:
            response = await self._client.get(path, headers=headers, params=params)
        except httpx2.TimeoutException as exc:
            raise SourceTimeoutError from exc
        except (httpx2.ConnectError, httpx2.NetworkError, httpx2.HTTPError) as exc:
            raise SourceError from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise SourceError
        try:
            payload = response.json()
        except ValueError as exc:
            raise InvalidSourceResponseError from exc
        if not isinstance(payload, dict):
            raise InvalidSourceResponseError
        return payload

    async def aclose(self) -> None:
        await self._client.aclose()


class DashboardSources(Protocol):
    async def customers(self, access_token: str, correlation_id: str) -> CustomerKpis: ...

    async def inventory(self, access_token: str, correlation_id: str) -> InventoryKpis: ...

    async def orders(self, access_token: str, correlation_id: str) -> OrderKpis: ...

    async def health(self, correlation_id: str) -> list[SourceResult]: ...

    async def aclose(self) -> None: ...


class HttpDashboardSources:
    """Aggregate only through existing service-owned APIs."""

    def __init__(
        self,
        settings: Settings,
        *,
        customer_client: ReadOnlyServiceClient | None = None,
        catalogue_client: ReadOnlyServiceClient | None = None,
        order_client: ReadOnlyServiceClient | None = None,
    ) -> None:
        timeout = settings.upstream_timeout_seconds
        self._customer = customer_client or ReadOnlyServiceClient(
            settings.customer_service_url, timeout
        )
        self._catalogue = catalogue_client or ReadOnlyServiceClient(
            settings.catalogue_service_url, timeout
        )
        self._order = order_client or ReadOnlyServiceClient(settings.order_service_url, timeout)
        self._maximum_records = settings.maximum_aggregate_records

    async def customers(self, access_token: str, correlation_id: str) -> CustomerKpis:
        count = 0
        offset = 0
        while True:
            payload = await self._customer.get_json(
                "/api/v1/admin/customers",
                correlation_id,
                access_token=access_token,
                params={"offset": offset, "limit": _PAGE_SIZE},
            )
            try:
                page = CustomerPage.model_validate(payload)
            except ValidationError as exc:
                raise InvalidSourceResponseError from exc
            page_count = len(page.items)
            count += page_count
            if count > self._maximum_records:
                raise InvalidSourceResponseError
            if page_count < _PAGE_SIZE:
                return CustomerKpis(customer_count=count)
            offset += page_count

    async def inventory(self, access_token: str, correlation_id: str) -> InventoryKpis:
        products_payload, inventory_payload = await asyncio.gather(
            self._catalogue.get_json(
                "/api/v1/products",
                correlation_id,
                access_token=access_token,
                params={"offset": 0, "limit": 1},
            ),
            self._catalogue.get_json(
                "/api/v1/inventory/statistics",
                correlation_id,
                access_token=access_token,
            ),
        )
        try:
            products = ProductPage.model_validate(products_payload)
            inventory = InventoryStatistics.model_validate(inventory_payload)
        except ValidationError as exc:
            raise InvalidSourceResponseError from exc
        if inventory.reserved_units > inventory.total_units_on_hand:
            raise InvalidSourceResponseError
        if inventory.available_units != inventory.total_units_on_hand - inventory.reserved_units:
            raise InvalidSourceResponseError
        classified = (
            inventory.in_stock_products
            + inventory.low_stock_products
            + inventory.out_of_stock_products
        )
        if classified != inventory.total_products_tracked:
            raise InvalidSourceResponseError
        return InventoryKpis(
            product_count=products.total,
            total_products_tracked=inventory.total_products_tracked,
            in_stock_count=inventory.in_stock_products,
            low_stock_count=inventory.low_stock_products,
            out_of_stock_count=inventory.out_of_stock_products,
            total_units_on_hand=inventory.total_units_on_hand,
            reserved_units=inventory.reserved_units,
            available_units=inventory.available_units,
            calculated_at=inventory.calculated_at,
        )

    async def orders(self, access_token: str, correlation_id: str) -> OrderKpis:
        offset = 0
        expected_total: int | None = None
        status_counts = {status: 0 for status in _ORDER_STATUSES}
        revenue: dict[str, Decimal] = {}
        observed = 0

        while expected_total is None or offset < expected_total:
            payload = await self._order.get_json(
                "/api/v1/orders/admin",
                correlation_id,
                access_token=access_token,
                params={"offset": offset, "limit": _PAGE_SIZE, "sort": "created_at_asc"},
            )
            try:
                page = OrderPage.model_validate(payload)
            except ValidationError as exc:
                raise InvalidSourceResponseError from exc
            if expected_total is None:
                expected_total = page.total
                if expected_total > self._maximum_records:
                    raise InvalidSourceResponseError
            elif page.total != expected_total:
                raise InvalidSourceResponseError
            if not page.items and offset < expected_total:
                raise InvalidSourceResponseError
            for item in page.items:
                status = item.status.upper()
                if status not in _ORDER_STATUSES:
                    raise InvalidSourceResponseError
                currency = item.currency_code.upper()
                status_counts[status] += 1
                if status in _REVENUE_STATUSES:
                    revenue[currency] = revenue.get(currency, Decimal("0")) + item.total
            observed += len(page.items)
            offset += len(page.items)

        if expected_total is None or observed != expected_total:
            raise InvalidSourceResponseError
        eligible = (
            status_counts["CONFIRMED"] + status_counts["PROCESSING"] + status_counts["FULFILLED"]
        )
        fulfilment_rate = (
            (Decimal(status_counts["FULFILLED"]) / Decimal(eligible) * Decimal("100"))
            if eligible
            else Decimal("0")
        ).quantize(Decimal("0.01"))
        normalized_revenue = {
            currency: amount.quantize(Decimal("0.0001"))
            for currency, amount in sorted(revenue.items())
        }
        return OrderKpis(
            total_orders=expected_total,
            simulated_revenue_by_currency=normalized_revenue,
            confirmed_orders=status_counts["CONFIRMED"],
            processing_orders=status_counts["PROCESSING"],
            fulfilled_orders=status_counts["FULFILLED"],
            cancelled_orders=status_counts["CANCELLED"],
            failed_orders=status_counts["FAILED"],
            fulfilment_rate=fulfilment_rate,
        )

    async def health(self, correlation_id: str) -> list[SourceResult]:
        clients = (
            ("customer-service", self._customer),
            ("catalogue-service", self._catalogue),
            ("order-service", self._order),
        )

        async def check(service: str, client: ReadOnlyServiceClient) -> SourceResult:
            try:
                payload = await client.get_json("/health/ready", correlation_id)
                document = HealthDocument.model_validate(payload)
                if document.status != "ready":
                    raise SourceError
                return SourceResult(service, True, DependencyState.AVAILABLE)
            except ValidationError:
                return SourceResult(service, None, DependencyState.INVALID_RESPONSE)
            except SourceError as exc:
                return SourceResult(service, None, exc.state)

        return list(await asyncio.gather(*(check(name, client) for name, client in clients)))

    async def aclose(self) -> None:
        await asyncio.gather(
            self._customer.aclose(), self._catalogue.aclose(), self._order.aclose()
        )
