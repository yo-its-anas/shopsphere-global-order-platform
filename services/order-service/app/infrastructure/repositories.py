"""SQLAlchemy repository and unit-of-work adapters."""

from __future__ import annotations

from types import TracebackType
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import CartItem, CartStatus, ShoppingCart
from app.infrastructure.database import SessionFactory
from app.infrastructure.orm_models import CartItemRecord, ShoppingCartRecord


def _cart_from_record(record: ShoppingCartRecord) -> ShoppingCart:
    return ShoppingCart(
        id=record.id,
        customer_identity_subject=record.customer_identity_subject,
        currency_code=record.currency_code,
        status=CartStatus(record.status),
        version=record.version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _item_from_record(record: CartItemRecord) -> CartItem:
    return CartItem(
        id=record.id,
        cart_id=record.cart_id,
        product_id=record.product_id,
        quantity=record.quantity,
        display_sku=record.display_sku,
        display_name=record.display_name,
        display_unit_price=record.display_unit_price,
        display_currency_code=record.display_currency_code,
        display_quantity_available=record.display_quantity_available,
        snapshot_at=record.snapshot_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyCartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_cart(
        self, customer_subject: str, currency_code: str, *, for_update: bool = False
    ) -> ShoppingCart | None:
        statement = select(ShoppingCartRecord).where(
            ShoppingCartRecord.customer_identity_subject == customer_subject,
            ShoppingCartRecord.currency_code == currency_code,
            ShoppingCartRecord.status == CartStatus.ACTIVE.value,
        )
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _cart_from_record(record) if record else None

    async def get_cart_by_id(
        self, cart_id: UUID, *, for_update: bool = False
    ) -> ShoppingCart | None:
        statement = select(ShoppingCartRecord).where(ShoppingCartRecord.id == cart_id)
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _cart_from_record(record) if record else None

    def add_cart(self, cart: ShoppingCart) -> None:
        self._session.add(
            ShoppingCartRecord(
                id=cart.id,
                customer_identity_subject=cart.customer_identity_subject,
                currency_code=cart.currency_code,
                status=cart.status.value,
                version=cart.version,
                created_at=cart.created_at,
                updated_at=cart.updated_at,
            )
        )

    async def update_cart(self, cart: ShoppingCart, expected_version: int) -> bool:
        result = await self._session.execute(
            update(ShoppingCartRecord)
            .where(
                ShoppingCartRecord.id == cart.id,
                ShoppingCartRecord.version == expected_version,
            )
            .values(version=cart.version, updated_at=cart.updated_at)
        )
        return result.rowcount == 1

    async def list_items(self, cart_id: UUID) -> list[CartItem]:
        records = await self._session.scalars(
            select(CartItemRecord)
            .where(CartItemRecord.cart_id == cart_id)
            .order_by(CartItemRecord.created_at, CartItemRecord.id)
        )
        return [_item_from_record(record) for record in records]

    async def get_item_by_product(
        self, cart_id: UUID, product_id: UUID, *, for_update: bool = False
    ) -> CartItem | None:
        statement = select(CartItemRecord).where(
            CartItemRecord.cart_id == cart_id,
            CartItemRecord.product_id == product_id,
        )
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _item_from_record(record) if record else None

    async def get_item(
        self, cart_id: UUID, item_id: UUID, *, for_update: bool = False
    ) -> CartItem | None:
        statement = select(CartItemRecord).where(
            CartItemRecord.cart_id == cart_id,
            CartItemRecord.id == item_id,
        )
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _item_from_record(record) if record else None

    def add_item(self, item: CartItem) -> None:
        self._session.add(
            CartItemRecord(
                id=item.id,
                cart_id=item.cart_id,
                product_id=item.product_id,
                quantity=item.quantity,
                display_sku=item.display_sku,
                display_name=item.display_name,
                display_unit_price=item.display_unit_price,
                display_currency_code=item.display_currency_code,
                display_quantity_available=item.display_quantity_available,
                snapshot_at=item.snapshot_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )

    async def update_item(self, item: CartItem) -> None:
        await self._session.execute(
            update(CartItemRecord)
            .where(CartItemRecord.id == item.id, CartItemRecord.cart_id == item.cart_id)
            .values(
                quantity=item.quantity,
                display_sku=item.display_sku,
                display_name=item.display_name,
                display_unit_price=item.display_unit_price,
                display_currency_code=item.display_currency_code,
                display_quantity_available=item.display_quantity_available,
                snapshot_at=item.snapshot_at,
                updated_at=item.updated_at,
            )
        )

    async def delete_item(self, item: CartItem) -> None:
        await self._session.execute(
            delete(CartItemRecord).where(
                CartItemRecord.id == item.id, CartItemRecord.cart_id == item.cart_id
            )
        )

    async def clear_items(self, cart_id: UUID) -> None:
        await self._session.execute(delete(CartItemRecord).where(CartItemRecord.cart_id == cart_id))


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.carts: SqlAlchemyCartRepository

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.carts = SqlAlchemyCartRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exc_type is not None:
            await self._session.rollback()
        await self._session.close()

    async def flush(self) -> None:
        if self._session is not None:
            await self._session.flush()

    async def commit(self) -> None:
        if self._session is not None:
            await self._session.commit()
