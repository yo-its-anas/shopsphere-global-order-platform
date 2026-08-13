"""SQLAlchemy implementations of Product Catalogue repository contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import TracebackType
from uuid import UUID

from sqlalchemy import Select, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.events import DomainEvent
from app.domain.models import (
    AvailabilityState,
    InventoryItem,
    InventoryMovement,
    InventoryMovementType,
    InventoryReservation,
    InventoryReservationStatus,
    Product,
    ProductCategory,
    ProductPrice,
    ProductStatus,
)
from app.infrastructure.orm_models import (
    DomainEventOutboxRecord,
    InventoryItemRecord,
    InventoryMovementRecord,
    InventoryReservationRecord,
    ProductCategoryRecord,
    ProductPriceRecord,
    ProductRecord,
)


def _category_from_record(record: ProductCategoryRecord) -> ProductCategory:
    return ProductCategory(
        id=record.id,
        name=record.name,
        slug=record.slug,
        description=record.description,
        is_active=record.is_active,
        parent_id=record.parent_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _product_from_record(record: ProductRecord) -> Product:
    return Product(
        id=record.id,
        sku=record.sku,
        name=record.name,
        description=record.description,
        category_id=record.category_id,
        status=ProductStatus(record.status),
        is_searchable=record.is_searchable,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _price_from_record(record: ProductPriceRecord) -> ProductPrice:
    return ProductPrice(
        id=record.id,
        product_id=record.product_id,
        amount=record.amount,
        currency_code=record.currency_code,
        is_active=record.is_active,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _inventory_from_record(record: InventoryItemRecord) -> InventoryItem:
    return InventoryItem(
        id=record.id,
        product_id=record.product_id,
        location_code=record.location_code,
        quantity_on_hand=record.quantity_on_hand,
        quantity_reserved=record.quantity_reserved,
        reorder_threshold=record.reorder_threshold,
        version=record.version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _movement_from_record(record: InventoryMovementRecord) -> InventoryMovement:
    return InventoryMovement(
        id=record.id,
        inventory_item_id=record.inventory_item_id,
        product_id=record.product_id,
        movement_type=InventoryMovementType(record.movement_type),
        quantity_delta=record.quantity_delta,
        reserved_delta=record.reserved_delta,
        previous_quantity_on_hand=record.previous_quantity_on_hand,
        resulting_quantity_on_hand=record.resulting_quantity_on_hand,
        previous_quantity_reserved=record.previous_quantity_reserved,
        resulting_quantity_reserved=record.resulting_quantity_reserved,
        reason=record.reason,
        reference=record.reference,
        actor_subject=record.actor_subject,
        correlation_id=record.correlation_id,
        idempotency_key=record.idempotency_key,
        occurred_at=record.occurred_at,
    )


def _reservation_from_record(record: InventoryReservationRecord) -> InventoryReservation:
    return InventoryReservation(
        id=record.id,
        inventory_item_id=record.inventory_item_id,
        product_id=record.product_id,
        quantity=record.quantity,
        external_reference=record.external_reference,
        status=InventoryReservationStatus(record.status),
        expires_at=record.expires_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyCatalogueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_category(self, category: ProductCategory) -> None:
        self._session.add(
            ProductCategoryRecord(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                is_active=category.is_active,
                parent_id=category.parent_id,
                created_at=category.created_at,
                updated_at=category.updated_at,
            )
        )

    async def get_category(self, category_id: UUID) -> ProductCategory | None:
        record = await self._session.get(ProductCategoryRecord, category_id)
        return _category_from_record(record) if record else None

    async def get_category_by_slug(self, slug: str) -> ProductCategory | None:
        record = await self._session.scalar(
            select(ProductCategoryRecord).where(ProductCategoryRecord.slug == slug)
        )
        return _category_from_record(record) if record else None

    async def list_categories(
        self, *, active: bool | None, offset: int, limit: int
    ) -> tuple[list[ProductCategory], int]:
        statement: Select[tuple[ProductCategoryRecord]] = select(ProductCategoryRecord)
        if active is not None:
            statement = statement.where(ProductCategoryRecord.is_active.is_(active))
        total = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        records = await self._session.scalars(
            statement.order_by(ProductCategoryRecord.name, ProductCategoryRecord.id)
            .offset(offset)
            .limit(limit)
        )
        return [_category_from_record(record) for record in records], int(total or 0)

    async def update_category(self, category: ProductCategory) -> None:
        record = await self._session.get(ProductCategoryRecord, category.id)
        if record is None:
            return
        record.name = category.name
        record.slug = category.slug
        record.description = category.description
        record.is_active = category.is_active
        record.parent_id = category.parent_id
        record.updated_at = category.updated_at

    def add_product(self, product: Product) -> None:
        self._session.add(
            ProductRecord(
                id=product.id,
                sku=product.sku,
                name=product.name,
                description=product.description,
                category_id=product.category_id,
                status=product.status.value,
                is_searchable=product.is_searchable,
                created_at=product.created_at,
                updated_at=product.updated_at,
            )
        )

    async def get_product(self, product_id: UUID) -> Product | None:
        record = await self._session.get(ProductRecord, product_id)
        return _product_from_record(record) if record else None

    async def get_product_by_sku(self, sku: str) -> Product | None:
        record = await self._session.scalar(select(ProductRecord).where(ProductRecord.sku == sku))
        return _product_from_record(record) if record else None

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
    ) -> tuple[list[Product], int]:
        statement: Select[tuple[ProductRecord]] = select(ProductRecord)
        if require_active_category:
            statement = statement.join(
                ProductCategoryRecord, ProductCategoryRecord.id == ProductRecord.category_id
            ).where(ProductCategoryRecord.is_active.is_(True))
        if query:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(
                    ProductRecord.name.ilike(pattern),
                    ProductRecord.sku.ilike(pattern),
                    ProductRecord.description.ilike(pattern),
                )
            )
        if sku:
            statement = statement.where(ProductRecord.sku == sku)
        if category_id:
            statement = statement.where(ProductRecord.category_id == category_id)
        if status:
            statement = statement.where(ProductRecord.status == status.value)
        if searchable is not None:
            statement = statement.where(ProductRecord.is_searchable.is_(searchable))

        total = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        sort_columns = {
            "created_at": ProductRecord.created_at,
            "name": ProductRecord.name,
            "sku": ProductRecord.sku,
            "updated_at": ProductRecord.updated_at,
        }
        sort_column = sort_columns[sort_by]
        ordering = sort_column.desc() if sort_direction == "desc" else sort_column.asc()
        records = await self._session.scalars(
            statement.order_by(ordering, ProductRecord.id.asc()).offset(offset).limit(limit)
        )
        return [_product_from_record(record) for record in records], int(total or 0)

    async def update_product(self, product: Product) -> None:
        record = await self._session.get(ProductRecord, product.id)
        if record is None:
            return
        record.name = product.name
        record.description = product.description
        record.category_id = product.category_id
        record.status = product.status.value
        record.is_searchable = product.is_searchable
        record.updated_at = product.updated_at

    def add_price(self, price: ProductPrice) -> None:
        self._session.add(
            ProductPriceRecord(
                id=price.id,
                product_id=price.product_id,
                amount=price.amount,
                currency_code=price.currency_code,
                is_active=price.is_active,
                effective_from=price.effective_from,
                effective_to=price.effective_to,
                created_at=price.created_at,
                updated_at=price.updated_at,
            )
        )

    async def list_prices(self, product_id: UUID, *, active_only: bool) -> list[ProductPrice]:
        statement = select(ProductPriceRecord).where(ProductPriceRecord.product_id == product_id)
        if active_only:
            statement = statement.where(ProductPriceRecord.is_active.is_(True))
        records = await self._session.scalars(
            statement.order_by(
                ProductPriceRecord.currency_code,
                ProductPriceRecord.effective_from.desc(),
                ProductPriceRecord.id.desc(),
            )
        )
        return [_price_from_record(record) for record in records]

    async def close_active_price(
        self, product_id: UUID, currency_code: str, effective_to: datetime
    ) -> None:
        await self._session.execute(
            update(ProductPriceRecord)
            .where(
                ProductPriceRecord.product_id == product_id,
                ProductPriceRecord.currency_code == currency_code,
                ProductPriceRecord.is_active.is_(True),
            )
            .values(is_active=False, effective_to=effective_to, updated_at=effective_to)
        )


class SqlAlchemyInventoryRepository:
    """Transactional inventory persistence with row locking and version guards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_item(self, item: InventoryItem) -> None:
        self._session.add(
            InventoryItemRecord(
                id=item.id,
                product_id=item.product_id,
                location_code=item.location_code,
                quantity_on_hand=item.quantity_on_hand,
                quantity_reserved=item.quantity_reserved,
                reorder_threshold=item.reorder_threshold,
                version=item.version,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )

    async def get_item(
        self, product_id: UUID, location_code: str, *, for_update: bool = False
    ) -> InventoryItem | None:
        statement = select(InventoryItemRecord).where(
            InventoryItemRecord.product_id == product_id,
            InventoryItemRecord.location_code == location_code,
        )
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _inventory_from_record(record) if record else None

    async def update_item(self, item: InventoryItem, expected_version: int) -> bool:
        result = await self._session.execute(
            update(InventoryItemRecord)
            .where(
                InventoryItemRecord.id == item.id,
                InventoryItemRecord.version == expected_version,
            )
            .values(
                quantity_on_hand=item.quantity_on_hand,
                quantity_reserved=item.quantity_reserved,
                reorder_threshold=item.reorder_threshold,
                version=item.version,
                updated_at=item.updated_at,
            )
        )
        return bool(result.rowcount == 1)

    async def list_items(
        self,
        *,
        state: AvailabilityState | None,
        location_code: str,
        offset: int,
        limit: int,
    ) -> tuple[list[InventoryItem], int]:
        available = InventoryItemRecord.quantity_on_hand - InventoryItemRecord.quantity_reserved
        statement: Select[tuple[InventoryItemRecord]] = select(InventoryItemRecord).where(
            InventoryItemRecord.location_code == location_code
        )
        if state is AvailabilityState.OUT_OF_STOCK:
            statement = statement.where(available == 0)
        elif state is AvailabilityState.LOW_STOCK:
            statement = statement.where(
                available > 0, available <= InventoryItemRecord.reorder_threshold
            )
        elif state is AvailabilityState.IN_STOCK:
            statement = statement.where(available > InventoryItemRecord.reorder_threshold)
        total = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        records = await self._session.scalars(
            statement.order_by(InventoryItemRecord.updated_at.desc(), InventoryItemRecord.id)
            .offset(offset)
            .limit(limit)
        )
        return [_inventory_from_record(record) for record in records], int(total or 0)

    def add_movement(self, movement: InventoryMovement) -> None:
        self._session.add(
            InventoryMovementRecord(
                id=movement.id,
                inventory_item_id=movement.inventory_item_id,
                product_id=movement.product_id,
                movement_type=movement.movement_type.value,
                quantity_delta=movement.quantity_delta,
                reserved_delta=movement.reserved_delta,
                previous_quantity_on_hand=movement.previous_quantity_on_hand,
                resulting_quantity_on_hand=movement.resulting_quantity_on_hand,
                previous_quantity_reserved=movement.previous_quantity_reserved,
                resulting_quantity_reserved=movement.resulting_quantity_reserved,
                reason=movement.reason,
                reference=movement.reference,
                actor_subject=movement.actor_subject,
                correlation_id=movement.correlation_id,
                idempotency_key=movement.idempotency_key,
                occurred_at=movement.occurred_at,
            )
        )

    async def get_movement_by_idempotency_key(
        self, idempotency_key: str
    ) -> InventoryMovement | None:
        record = await self._session.scalar(
            select(InventoryMovementRecord).where(
                InventoryMovementRecord.idempotency_key == idempotency_key
            )
        )
        return _movement_from_record(record) if record else None

    async def list_movements(
        self, inventory_item_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[InventoryMovement], int]:
        statement = select(InventoryMovementRecord).where(
            InventoryMovementRecord.inventory_item_id == inventory_item_id
        )
        total = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        records = await self._session.scalars(
            statement.order_by(
                InventoryMovementRecord.occurred_at.desc(), InventoryMovementRecord.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
        return [_movement_from_record(record) for record in records], int(total or 0)

    async def statistics(self, location_code: str) -> dict[str, int]:
        available = InventoryItemRecord.quantity_on_hand - InventoryItemRecord.quantity_reserved
        statement = select(
            func.count(InventoryItemRecord.id).label("total_products_tracked"),
            func.coalesce(
                func.sum(case((available > InventoryItemRecord.reorder_threshold, 1), else_=0)),
                0,
            ).label("in_stock_products"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (available > 0) & (available <= InventoryItemRecord.reorder_threshold),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("low_stock_products"),
            func.coalesce(func.sum(case((available == 0, 1), else_=0)), 0).label(
                "out_of_stock_products"
            ),
            func.coalesce(func.sum(InventoryItemRecord.quantity_on_hand), 0).label(
                "total_units_on_hand"
            ),
            func.coalesce(func.sum(InventoryItemRecord.quantity_reserved), 0).label(
                "reserved_units"
            ),
            func.coalesce(func.sum(available), 0).label("available_units"),
        ).where(InventoryItemRecord.location_code == location_code)
        row = (await self._session.execute(statement)).one()
        return {key: int(value) for key, value in row._mapping.items()}

    def add_reservation(self, reservation: InventoryReservation) -> None:
        self._session.add(
            InventoryReservationRecord(
                id=reservation.id,
                inventory_item_id=reservation.inventory_item_id,
                product_id=reservation.product_id,
                quantity=reservation.quantity,
                external_reference=reservation.external_reference,
                status=reservation.status.value,
                expires_at=reservation.expires_at,
                created_at=reservation.created_at,
                updated_at=reservation.updated_at,
            )
        )

    async def get_reservation(
        self, reservation_id: UUID, *, for_update: bool = False
    ) -> InventoryReservation | None:
        statement = select(InventoryReservationRecord).where(
            InventoryReservationRecord.id == reservation_id
        )
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _reservation_from_record(record) if record else None

    async def get_reservation_by_external_reference(
        self, external_reference: str, *, for_update: bool = False
    ) -> InventoryReservation | None:
        statement = select(InventoryReservationRecord).where(
            InventoryReservationRecord.external_reference == external_reference
        )
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _reservation_from_record(record) if record else None

    async def update_reservation(self, reservation: InventoryReservation) -> None:
        await self._session.execute(
            update(InventoryReservationRecord)
            .where(InventoryReservationRecord.id == reservation.id)
            .values(
                status=reservation.status.value,
                expires_at=reservation.expires_at,
                updated_at=reservation.updated_at,
            )
        )


class SqlAlchemyOutboxRepository:
    """Adds event intent to the same transaction as the aggregate mutation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event: DomainEvent) -> None:
        self._session.add(
            DomainEventOutboxRecord(
                event_id=event.event_id,
                event_type=event.event_type,
                event_version=event.event_version,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                occurred_at=event.occurred_at,
                correlation_id=event.correlation_id,
                producer=event.producer,
                payload=event.payload,
                status="pending",
                attempts=0,
                available_at=event.occurred_at,
            )
        )


class SqlAlchemyOutboxStore:
    """Lease and acknowledge pending outbox rows without holding locks during I/O."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def claim(self, batch_size: int, lease_seconds: int) -> list[DomainEvent]:
        now = datetime.now(timezone.utc)
        expired_before = now - timedelta(seconds=lease_seconds)
        async with self._session_factory() as session, session.begin():
            records = list(
                await session.scalars(
                    select(DomainEventOutboxRecord)
                    .where(
                        DomainEventOutboxRecord.status == "pending",
                        DomainEventOutboxRecord.available_at <= now,
                        or_(
                            DomainEventOutboxRecord.locked_at.is_(None),
                            DomainEventOutboxRecord.locked_at < expired_before,
                        ),
                    )
                    .order_by(
                        DomainEventOutboxRecord.occurred_at,
                        DomainEventOutboxRecord.event_id,
                    )
                    .with_for_update(skip_locked=True)
                    .limit(batch_size)
                )
            )
            for record in records:
                record.locked_at = now
                record.attempts += 1
            return [
                DomainEvent(
                    event_id=record.event_id,
                    event_type=record.event_type,
                    event_version=record.event_version,
                    aggregate_type=record.aggregate_type,
                    aggregate_id=record.aggregate_id,
                    occurred_at=record.occurred_at,
                    correlation_id=record.correlation_id,
                    producer=record.producer,
                    payload=record.payload,
                )
                for record in records
            ]

    async def mark_published(self, event_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(DomainEventOutboxRecord)
                .where(
                    DomainEventOutboxRecord.event_id == event_id,
                    DomainEventOutboxRecord.status == "pending",
                )
                .values(
                    status="published",
                    published_at=now,
                    locked_at=None,
                    last_error_code=None,
                )
            )

    async def release_for_retry(
        self, event_id: UUID, delay_seconds: float, error_code: str
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(DomainEventOutboxRecord)
                .where(
                    DomainEventOutboxRecord.event_id == event_id,
                    DomainEventOutboxRecord.status == "pending",
                )
                .values(
                    available_at=now + timedelta(seconds=delay_seconds),
                    locked_at=None,
                    last_error_code=error_code,
                )
            )


class SqlAlchemyUnitOfWork:
    """One database transaction for one catalogue operation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.catalogue = SqlAlchemyCatalogueRepository(self._session)
        self.inventory = SqlAlchemyInventoryRepository(self._session)
        self.outbox = SqlAlchemyOutboxRepository(self._session)
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
