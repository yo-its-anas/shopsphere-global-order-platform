"""Fixed-origin catalogue-service client for cart display validation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx2

from app.core.errors import DependencyUnavailableError, ProductUnavailableError
from app.domain.models import CatalogueProductSnapshot


class CatalogueHttpClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = f"{base_url.rstrip('/')}/"
        self._timeout_seconds = timeout_seconds
        self._transport = transport

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
                price_response = await client.get(f"products/{product_id}/prices", headers=headers)
                if price_response.status_code == 404:
                    raise ProductUnavailableError
                if price_response.status_code != 200:
                    raise DependencyUnavailableError
                availability_response = await client.get(
                    f"inventory/products/{product_id}/availability", headers=headers
                )
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
