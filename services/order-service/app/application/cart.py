"""Shopping-cart application service."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import replace
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, InvalidOperationError, ResourceNotFoundError
from app.domain.models import CartItem, ShoppingCart, utc_now
from app.domain.repositories import CatalogueProductProvider, UnitOfWork

logger = logging.getLogger(__name__)
UnitOfWorkFactory = Callable[[], UnitOfWork]


class CartService:
    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        catalogue: CatalogueProductProvider,
        currency_code: str,
        max_item_quantity: int,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._catalogue = catalogue
        self._currency_code = currency_code
        self._max_item_quantity = max_item_quantity

    async def get_current(self, customer_subject: str) -> tuple[ShoppingCart, Sequence[CartItem]]:
        cart = await self._get_or_create_cart(customer_subject)
        return cart, await self._items(cart.id)

    async def add_item(
        self,
        customer_subject: str,
        product_id: UUID,
        quantity: int,
        access_token: str,
        correlation_id: str,
    ) -> tuple[ShoppingCart, Sequence[CartItem]]:
        self._validate_quantity(quantity)
        snapshot = await self._catalogue.get_product_snapshot(
            product_id,
            self._currency_code,
            access_token,
            correlation_id,
        )
        cart = await self._get_or_create_cart(customer_subject)
        async with self._unit_of_work_factory() as work:
            current_cart = await work.carts.get_cart_by_id(cart.id, for_update=True)
            if current_cart is None or current_cart.customer_identity_subject != customer_subject:
                raise ResourceNotFoundError
            item = await work.carts.get_item_by_product(cart.id, product_id, for_update=True)
            resulting_quantity = quantity if item is None else item.quantity + quantity
            self._validate_quantity(resulting_quantity)
            if item is None:
                work.carts.add_item(
                    CartItem(
                        cart_id=cart.id,
                        product_id=product_id,
                        quantity=resulting_quantity,
                        display_sku=snapshot.sku,
                        display_name=snapshot.name,
                        display_unit_price=snapshot.unit_price,
                        display_currency_code=snapshot.currency_code,
                        display_quantity_available=snapshot.quantity_available,
                        snapshot_at=snapshot.captured_at,
                    )
                )
            else:
                item = replace(
                    item,
                    quantity=resulting_quantity,
                    display_sku=snapshot.sku,
                    display_name=snapshot.name,
                    display_unit_price=snapshot.unit_price,
                    display_currency_code=snapshot.currency_code,
                    display_quantity_available=snapshot.quantity_available,
                    snapshot_at=snapshot.captured_at,
                    updated_at=utc_now(),
                )
                await work.carts.update_item(item)
            await self._touch_cart(work, current_cart)
            await work.flush()
            await work.commit()
        self._log_mutation("cart_item_added", customer_subject, cart.id, product_id, correlation_id)
        return await self.get_current(customer_subject)

    async def update_item(
        self,
        customer_subject: str,
        item_id: UUID,
        quantity: int,
        correlation_id: str,
    ) -> tuple[ShoppingCart, Sequence[CartItem]]:
        self._validate_quantity(quantity)
        cart = await self._require_cart(customer_subject)
        async with self._unit_of_work_factory() as work:
            current_cart = await work.carts.get_cart_by_id(cart.id, for_update=True)
            if current_cart is None or current_cart.customer_identity_subject != customer_subject:
                raise ResourceNotFoundError
            item = await work.carts.get_item(cart.id, item_id, for_update=True)
            if item is None:
                raise ResourceNotFoundError
            await work.carts.update_item(replace(item, quantity=quantity, updated_at=utc_now()))
            await self._touch_cart(work, current_cart)
            await work.flush()
            await work.commit()
        self._log_mutation(
            "cart_item_updated", customer_subject, cart.id, item.product_id, correlation_id
        )
        return await self.get_current(customer_subject)

    async def remove_item(
        self, customer_subject: str, item_id: UUID, correlation_id: str
    ) -> tuple[ShoppingCart, Sequence[CartItem]]:
        cart = await self._require_cart(customer_subject)
        async with self._unit_of_work_factory() as work:
            current_cart = await work.carts.get_cart_by_id(cart.id, for_update=True)
            if current_cart is None or current_cart.customer_identity_subject != customer_subject:
                raise ResourceNotFoundError
            item = await work.carts.get_item(cart.id, item_id, for_update=True)
            if item is None:
                raise ResourceNotFoundError
            await work.carts.delete_item(item)
            await self._touch_cart(work, current_cart)
            await work.commit()
        self._log_mutation(
            "cart_item_removed", customer_subject, cart.id, item.product_id, correlation_id
        )
        return await self.get_current(customer_subject)

    async def clear(
        self, customer_subject: str, correlation_id: str
    ) -> tuple[ShoppingCart, Sequence[CartItem]]:
        cart = await self._require_cart(customer_subject)
        async with self._unit_of_work_factory() as work:
            current_cart = await work.carts.get_cart_by_id(cart.id, for_update=True)
            if current_cart is None or current_cart.customer_identity_subject != customer_subject:
                raise ResourceNotFoundError
            await work.carts.clear_items(cart.id)
            await self._touch_cart(work, current_cart)
            await work.commit()
        logger.info(
            "cart_cleared",
            extra={
                "event": "cart_cleared",
                "cart_id": str(cart.id),
                "actor_subject": customer_subject,
                "correlation_id": correlation_id,
            },
        )
        return await self.get_current(customer_subject)

    async def _get_or_create_cart(self, customer_subject: str) -> ShoppingCart:
        async with self._unit_of_work_factory() as work:
            cart = await work.carts.get_active_cart(customer_subject, self._currency_code)
            if cart is not None:
                return cart
            cart = ShoppingCart(
                customer_identity_subject=customer_subject,
                currency_code=self._currency_code,
            )
            work.carts.add_cart(cart)
            try:
                await work.flush()
                await work.commit()
                return cart
            except IntegrityError:
                pass
        async with self._unit_of_work_factory() as retry_work:
            cart = await retry_work.carts.get_active_cart(customer_subject, self._currency_code)
            if cart is None:
                raise ConflictError
            return cart

    async def _require_cart(self, customer_subject: str) -> ShoppingCart:
        async with self._unit_of_work_factory() as work:
            cart = await work.carts.get_active_cart(customer_subject, self._currency_code)
            if cart is None:
                raise ResourceNotFoundError
            return cart

    async def _items(self, cart_id: UUID) -> Sequence[CartItem]:
        async with self._unit_of_work_factory() as work:
            return await work.carts.list_items(cart_id)

    async def _touch_cart(self, work: UnitOfWork, cart: ShoppingCart) -> None:
        updated = replace(cart, version=cart.version + 1, updated_at=utc_now())
        if not await work.carts.update_cart(updated, cart.version):
            raise ConflictError

    def _validate_quantity(self, quantity: int) -> None:
        if quantity < 1 or quantity > self._max_item_quantity:
            raise InvalidOperationError

    @staticmethod
    def _log_mutation(
        event: str,
        customer_subject: str,
        cart_id: UUID,
        product_id: UUID,
        correlation_id: str,
    ) -> None:
        logger.info(
            event,
            extra={
                "event": event,
                "cart_id": str(cart_id),
                "product_id": str(product_id),
                "actor_subject": customer_subject,
                "correlation_id": correlation_id,
            },
        )
