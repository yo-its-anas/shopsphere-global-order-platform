"""Repository and transaction contracts for the Catalogue boundary."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from types import TracebackType
from typing import Protocol
from uuid import UUID

from app.domain.models import Product, ProductCategory, ProductPrice, ProductStatus


class CatalogueRepository(Protocol):
    def add_category(self, category: ProductCategory) -> None: ...

    async def get_category(self, category_id: UUID) -> ProductCategory | None: ...

    async def get_category_by_slug(self, slug: str) -> ProductCategory | None: ...

    async def list_categories(
        self, *, active: bool | None, offset: int, limit: int
    ) -> tuple[Sequence[ProductCategory], int]: ...

    async def update_category(self, category: ProductCategory) -> None: ...

    def add_product(self, product: Product) -> None: ...

    async def get_product(self, product_id: UUID) -> Product | None: ...

    async def get_product_by_sku(self, sku: str) -> Product | None: ...

    async def list_products(
        self,
        *,
        query: str | None,
        sku: str | None,
        category_id: UUID | None,
        status: ProductStatus | None,
        searchable: bool | None,
        require_active_category: bool,
        offset: int,
        limit: int,
        sort_by: str,
        sort_direction: str,
    ) -> tuple[Sequence[Product], int]: ...

    async def update_product(self, product: Product) -> None: ...

    def add_price(self, price: ProductPrice) -> None: ...

    async def list_prices(
        self, product_id: UUID, *, active_only: bool
    ) -> Sequence[ProductPrice]: ...

    async def close_active_price(
        self, product_id: UUID, currency_code: str, effective_to: datetime
    ) -> None: ...


class UnitOfWork(Protocol):
    catalogue: CatalogueRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...
