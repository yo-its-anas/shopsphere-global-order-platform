"""Repository and integration contracts for the cart capability."""

from __future__ import annotations

from collections.abc import Awaitable, Sequence
from types import TracebackType
from typing import Protocol
from uuid import UUID

from app.domain.models import CartItem, CatalogueProductSnapshot, ShoppingCart


class CartRepository(Protocol):
    async def get_active_cart(
        self, customer_subject: str, currency_code: str, *, for_update: bool = False
    ) -> ShoppingCart | None: ...

    async def get_cart_by_id(
        self, cart_id: UUID, *, for_update: bool = False
    ) -> ShoppingCart | None: ...

    def add_cart(self, cart: ShoppingCart) -> None: ...

    async def update_cart(self, cart: ShoppingCart, expected_version: int) -> bool: ...

    async def list_items(self, cart_id: UUID) -> Sequence[CartItem]: ...

    async def get_item_by_product(
        self, cart_id: UUID, product_id: UUID, *, for_update: bool = False
    ) -> CartItem | None: ...

    async def get_item(
        self, cart_id: UUID, item_id: UUID, *, for_update: bool = False
    ) -> CartItem | None: ...

    def add_item(self, item: CartItem) -> None: ...

    async def update_item(self, item: CartItem) -> None: ...

    async def delete_item(self, item: CartItem) -> None: ...

    async def clear_items(self, cart_id: UUID) -> None: ...


class UnitOfWork(Protocol):
    carts: CartRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...


class CatalogueProductProvider(Protocol):
    def get_product_snapshot(
        self,
        product_id: UUID,
        currency_code: str,
        access_token: str,
        correlation_id: str,
    ) -> Awaitable[CatalogueProductSnapshot]: ...
