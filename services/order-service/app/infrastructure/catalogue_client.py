"""Fixed-origin catalogue-service client for cart display validation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from time import monotonic
from typing import Any
from uuid import UUID

import httpx2

from app.core.errors import DependencyUnavailableError, ProductUnavailableError
from app.core.telemetry import Telemetry
from app.domain.models import CatalogueProductSnapshot, InventoryReservationReceipt


class KeycloakServiceTokenProvider:
    """Acquire and briefly cache a confidential client token without logging it."""

    def __init__(
        self, token_url: str, client_id: str, client_secret: str, timeout_seconds: float
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout_seconds = timeout_seconds
        self._token: str | None = None
        self._expires_at = 0.0

    async def get_token(self) -> str:
        if self._token and monotonic() < self._expires_at:
            return self._token
        try:
            async with httpx2.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                )
                response.raise_for_status()
                payload = response.json()
            token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 60))
            if not isinstance(token, str) or not token:
                raise ValueError("Missing service access token")
        except (httpx2.HTTPError, TypeError, ValueError) as exc:
            raise DependencyUnavailableError from exc
        self._token = token
        self._expires_at = monotonic() + max(1, expires_in - 15)
        return token


class CatalogueHttpClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
        service_token_provider: KeycloakServiceTokenProvider | None = None,
        telemetry: Telemetry | None = None,
    ) -> None:
        self._base_url = f"{base_url.rstrip('/')}/"
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._service_token_provider = service_token_provider
        self._telemetry = telemetry or Telemetry(None, "order-service")

    async def get_product_snapshot(
        self,
        product_id: UUID,
        currency_code: str,
        access_token: str,
        correlation_id: str,
    ) -> CatalogueProductSnapshot:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "X-Request-ID": correlation_id,
        }
        try:
            with self._telemetry.client_span(
                "catalogue-service product snapshot",
                upstream_service="catalogue-service",
                method="GET",
            ) as span:
                self._telemetry.inject(headers)
                async with httpx2.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout_seconds,
                    transport=self._transport,
                ) as client:
                    product_response = await client.get(f"products/{product_id}", headers=headers)
                    if product_response.status_code == 404:
                        raise ProductUnavailableError
                    if product_response.status_code != 200:
                        raise DependencyUnavailableError
                    price_response = await client.get(
                        f"products/{product_id}/prices", headers=headers
                    )
                    if price_response.status_code == 404:
                        raise ProductUnavailableError
                    if price_response.status_code != 200:
                        raise DependencyUnavailableError
                    availability_response = await client.get(
                        f"inventory/products/{product_id}/availability", headers=headers
                    )
                    self._telemetry.set_http_status(span, availability_response.status_code)
        except (httpx2.TimeoutException, httpx2.NetworkError, httpx2.ConnectError) as exc:
            raise DependencyUnavailableError from exc
        except httpx2.HTTPError as exc:
            raise DependencyUnavailableError from exc

        try:
            product = product_response.json()
            prices = price_response.json().get("items", [])
            price = next(
                item
                for item in prices
                if item.get("currency_code") == currency_code and item.get("is_active") is True
            )
            amount = Decimal(str(price["amount"]))
            if (
                product.get("id") != str(product_id)
                or product.get("status") != "active"
                or product.get("is_searchable") is not True
                or amount <= 0
            ):
                raise ProductUnavailableError
            quantity_available: int | None = None
            if availability_response.status_code == 200:
                availability: dict[str, Any] = availability_response.json()
                candidate = availability.get("quantity_available")
                if isinstance(candidate, int) and candidate >= 0:
                    quantity_available = candidate
            elif availability_response.status_code not in {404}:
                raise DependencyUnavailableError
            return CatalogueProductSnapshot(
                product_id=product_id,
                sku=str(product["sku"]),
                name=str(product["name"]),
                status=str(product["status"]),
                is_searchable=bool(product["is_searchable"]),
                unit_price=amount,
                currency_code=currency_code,
                quantity_available=quantity_available,
            )
        except (KeyError, StopIteration, TypeError, ValueError, InvalidOperation) as exc:
            raise ProductUnavailableError from exc

    async def reserve_inventory(
        self,
        product_id: UUID,
        quantity: int,
        external_reference: str,
        correlation_id: str,
    ) -> InventoryReservationReceipt:
        token = await self._service_token()
        response = await self._request_service(
            "POST",
            "inventory/reservations",
            token,
            correlation_id,
            json={
                "product_id": str(product_id),
                "quantity": quantity,
                "external_reference": external_reference,
            },
        )
        if response.status_code in {400, 404, 409, 422}:
            raise ProductUnavailableError
        if response.status_code not in {200, 201}:
            raise DependencyUnavailableError
        return self._reservation_receipt(response, product_id, quantity, external_reference)

    async def release_inventory(
        self, reservation_id: UUID, correlation_id: str
    ) -> InventoryReservationReceipt:
        token = await self._service_token()
        response = await self._request_service(
            "POST",
            f"inventory/reservations/{reservation_id}/release",
            token,
            correlation_id,
        )
        if response.status_code not in {200, 201}:
            raise DependencyUnavailableError
        return self._reservation_receipt(response)

    async def consume_inventory(
        self, reservation_id: UUID, correlation_id: str
    ) -> InventoryReservationReceipt:
        token = await self._service_token()
        response = await self._request_service(
            "POST",
            f"inventory/reservations/{reservation_id}/consume",
            token,
            correlation_id,
        )
        if response.status_code not in {200, 201}:
            raise DependencyUnavailableError
        return self._reservation_receipt(response)

    async def _service_token(self) -> str:
        if self._service_token_provider is None:
            raise DependencyUnavailableError
        return await self._service_token_provider.get_token()

    async def _request_service(
        self,
        method: str,
        path: str,
        token: str,
        correlation_id: str,
        **kwargs: Any,
    ) -> httpx2.Response:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "X-Request-ID": correlation_id,
        }
        try:
            with self._telemetry.client_span(
                f"catalogue-service {method.upper()}",
                upstream_service="catalogue-service",
                method=method,
            ) as span:
                self._telemetry.inject(headers)
                async with httpx2.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.request(method, path, headers=headers, **kwargs)
                    self._telemetry.set_http_status(span, response.status_code)
                    return response
        except (httpx2.TimeoutException, httpx2.NetworkError, httpx2.ConnectError) as exc:
            raise DependencyUnavailableError from exc
        except httpx2.HTTPError as exc:
            raise DependencyUnavailableError from exc

    @staticmethod
    def _reservation_receipt(
        response: httpx2.Response,
        expected_product_id: UUID | None = None,
        expected_quantity: int | None = None,
        expected_reference: str | None = None,
    ) -> InventoryReservationReceipt:
        try:
            payload = response.json()["reservation"]
            receipt = InventoryReservationReceipt(
                reservation_id=UUID(str(payload["reservation_id"])),
                product_id=UUID(str(payload["product_id"])),
                quantity=int(payload["quantity"]),
                external_reference=str(payload["external_reference"]),
                status=str(payload["status"]),
            )
            if (
                (expected_product_id is not None and receipt.product_id != expected_product_id)
                or (expected_quantity is not None and receipt.quantity != expected_quantity)
                or (
                    expected_reference is not None
                    and receipt.external_reference != expected_reference
                )
            ):
                raise ValueError("Reservation response mismatch")
            return receipt
        except (KeyError, TypeError, ValueError) as exc:
            raise DependencyUnavailableError from exc
