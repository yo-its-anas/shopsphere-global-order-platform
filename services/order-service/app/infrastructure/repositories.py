"""SQLAlchemy repository and unit-of-work adapters."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import TracebackType
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import (
    CartItem,
    CartStatus,
    CheckoutAttempt,
    CheckoutAttemptStatus,
    Order,
    OrderAuditEvent,
    OrderDomainEvent,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    ShoppingCart,
)
from app.infrastructure.database import SessionFactory
from app.infrastructure.orm_models import (
    CartItemRecord,
    CheckoutAttemptRecord,
    OrderAuditEventRecord,
    OrderItemRecord,
    OrderOutboxRecord,
    OrderRecord,
    OrderStatusHistoryRecord,
    ShoppingCartRecord,
)


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


def _order_from_record(record: OrderRecord) -> Order:
    return Order(
        id=record.id,
        order_number=record.order_number,
        customer_identity_subject=record.customer_identity_subject,
        source_cart_id=record.source_cart_id,
        status=OrderStatus(record.status),
        currency_code=record.currency_code,
        subtotal=record.subtotal,
        total=record.total,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _order_item_from_record(record: OrderItemRecord) -> OrderItem:
    return OrderItem(
        id=record.id,
        order_id=record.order_id,
        product_id=record.product_id,
        sku=record.sku,
        product_name=record.product_name,
        quantity=record.quantity,
        unit_price=record.unit_price,
        currency_code=record.currency_code,
        line_total=record.line_total,
        reservation_id=record.reservation_id,
        created_at=record.created_at,
    )


def _attempt_from_record(record: CheckoutAttemptRecord) -> CheckoutAttempt:
    return CheckoutAttempt(
        id=record.id,
        customer_identity_subject=record.customer_identity_subject,
        idempotency_key=record.idempotency_key,
        source_cart_id=record.source_cart_id,
        source_cart_version=record.source_cart_version,
        request_fingerprint=record.request_fingerprint,
        reservation_plan=list(record.reservation_plan),
        status=CheckoutAttemptStatus(record.status),
        order_id=record.order_id,
        reservation_ids=list(record.reservation_ids),
        unresolved_reservations=list(record.unresolved_reservations),
        failure_code=record.failure_code,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _history_from_record(record: OrderStatusHistoryRecord) -> OrderStatusHistory:
    return OrderStatusHistory(
        id=record.id,
        order_id=record.order_id,
        status=OrderStatus(record.status),
        actor_subject=record.actor_subject,
        correlation_id=record.correlation_id,
        occurred_at=record.occurred_at,
    )


def _audit_from_record(record: OrderAuditEventRecord) -> OrderAuditEvent:
    return OrderAuditEvent(
        id=record.id,
        order_id=record.order_id,
        action=record.action,
        actor_subject=record.actor_subject,
        correlation_id=record.correlation_id,
        metadata=record.safe_metadata,
        occurred_at=record.occurred_at,
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
            .values(status=cart.status.value, version=cart.version, updated_at=cart.updated_at)
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


class SqlAlchemyOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_checkout_attempt(self, attempt: CheckoutAttempt) -> None:
        self._session.add(
            CheckoutAttemptRecord(
                id=attempt.id,
                customer_identity_subject=attempt.customer_identity_subject,
                idempotency_key=attempt.idempotency_key,
                source_cart_id=attempt.source_cart_id,
                source_cart_version=attempt.source_cart_version,
                request_fingerprint=attempt.request_fingerprint,
                reservation_plan=attempt.reservation_plan,
                status=attempt.status.value,
                order_id=attempt.order_id,
                reservation_ids=attempt.reservation_ids,
                unresolved_reservations=attempt.unresolved_reservations,
                failure_code=attempt.failure_code,
                created_at=attempt.created_at,
                updated_at=attempt.updated_at,
            )
        )

    async def get_checkout_attempt(
        self, customer_subject: str, idempotency_key: str, *, for_update: bool = False
    ) -> CheckoutAttempt | None:
        statement = select(CheckoutAttemptRecord).where(
            CheckoutAttemptRecord.customer_identity_subject == customer_subject,
            CheckoutAttemptRecord.idempotency_key == idempotency_key,
        )
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _attempt_from_record(record) if record else None

    async def update_checkout_attempt(self, attempt: CheckoutAttempt) -> None:
        await self._session.execute(
            update(CheckoutAttemptRecord)
            .where(CheckoutAttemptRecord.id == attempt.id)
            .values(
                status=attempt.status.value,
                order_id=attempt.order_id,
                reservation_ids=attempt.reservation_ids,
                unresolved_reservations=attempt.unresolved_reservations,
                failure_code=attempt.failure_code,
                updated_at=attempt.updated_at,
            )
        )

    def add_order(self, order: Order) -> None:
        self._session.add(
            OrderRecord(
                id=order.id,
                order_number=order.order_number,
                customer_identity_subject=order.customer_identity_subject,
                source_cart_id=order.source_cart_id,
                status=order.status.value,
                currency_code=order.currency_code,
                subtotal=order.subtotal,
                total=order.total,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )
        )

    async def get_order(self, order_id: UUID, *, for_update: bool = False) -> Order | None:
        statement = select(OrderRecord).where(OrderRecord.id == order_id)
        if for_update:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        return _order_from_record(record) if record else None

    async def list_orders(
        self,
        *,
        customer_subject: str | None,
        status: str | None,
        offset: int,
        limit: int,
        ascending: bool,
    ) -> tuple[list[Order], int]:
        statement = select(OrderRecord)
        if customer_subject is not None:
            statement = statement.where(OrderRecord.customer_identity_subject == customer_subject)
        if status is not None:
            statement = statement.where(OrderRecord.status == status)
        total = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        ordering = OrderRecord.created_at.asc() if ascending else OrderRecord.created_at.desc()
        records = await self._session.scalars(
            statement.order_by(ordering, OrderRecord.id).offset(offset).limit(limit)
        )
        return [_order_from_record(record) for record in records], int(total or 0)

    async def update_order(self, order: Order) -> None:
        await self._session.execute(
            update(OrderRecord)
            .where(OrderRecord.id == order.id)
            .values(status=order.status.value, updated_at=order.updated_at)
        )

    def add_order_item(self, item: OrderItem) -> None:
        self._session.add(
            OrderItemRecord(
                id=item.id,
                order_id=item.order_id,
                product_id=item.product_id,
                sku=item.sku,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency_code=item.currency_code,
                line_total=item.line_total,
                reservation_id=item.reservation_id,
                created_at=item.created_at,
            )
        )

    async def list_order_items(self, order_id: UUID) -> list[OrderItem]:
        records = await self._session.scalars(
            select(OrderItemRecord)
            .where(OrderItemRecord.order_id == order_id)
            .order_by(OrderItemRecord.created_at, OrderItemRecord.id)
        )
        return [_order_item_from_record(record) for record in records]

    def add_status_history(self, history: OrderStatusHistory) -> None:
        self._session.add(
            OrderStatusHistoryRecord(
                id=history.id,
                order_id=history.order_id,
                status=history.status.value,
                actor_subject=history.actor_subject,
                correlation_id=history.correlation_id,
                occurred_at=history.occurred_at,
            )
        )

    async def list_status_history(self, order_id: UUID) -> list[OrderStatusHistory]:
        records = await self._session.scalars(
            select(OrderStatusHistoryRecord)
            .where(OrderStatusHistoryRecord.order_id == order_id)
            .order_by(OrderStatusHistoryRecord.occurred_at, OrderStatusHistoryRecord.id)
        )
        return [_history_from_record(record) for record in records]

    def add_audit_event(self, event: OrderAuditEvent) -> None:
        self._session.add(
            OrderAuditEventRecord(
                id=event.id,
                order_id=event.order_id,
                action=event.action,
                actor_subject=event.actor_subject,
                correlation_id=event.correlation_id,
                safe_metadata=event.metadata,
                occurred_at=event.occurred_at,
            )
        )

    async def list_audit_events(
        self, order_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[OrderAuditEvent], int]:
        statement = select(OrderAuditEventRecord).where(OrderAuditEventRecord.order_id == order_id)
        total = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        records = await self._session.scalars(
            statement.order_by(OrderAuditEventRecord.occurred_at, OrderAuditEventRecord.id)
            .offset(offset)
            .limit(limit)
        )
        return [_audit_from_record(record) for record in records], int(total or 0)


class SqlAlchemyOrderOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event: OrderDomainEvent) -> None:
        self._session.add(
            OrderOutboxRecord(
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


class SqlAlchemyOrderOutboxStore:
    """Lease pending events without retaining database locks during Kafka I/O."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def claim(self, batch_size: int, lease_seconds: int) -> list[OrderDomainEvent]:
        now = datetime.now(timezone.utc)
        expired = now - timedelta(seconds=lease_seconds)
        async with self._session_factory() as session, session.begin():
            records = list(
                await session.scalars(
                    select(OrderOutboxRecord)
                    .where(
                        OrderOutboxRecord.status == "pending",
                        OrderOutboxRecord.available_at <= now,
                        or_(
                            OrderOutboxRecord.locked_at.is_(None),
                            OrderOutboxRecord.locked_at < expired,
                        ),
                    )
                    .order_by(OrderOutboxRecord.occurred_at, OrderOutboxRecord.event_id)
                    .with_for_update(skip_locked=True)
                    .limit(batch_size)
                )
            )
            for record in records:
                record.locked_at = now
                record.attempts += 1
            return [
                OrderDomainEvent(
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
                update(OrderOutboxRecord)
                .where(
                    OrderOutboxRecord.event_id == event_id,
                    OrderOutboxRecord.status == "pending",
                )
                .values(
                    status="published",
                    published_at=now,
                    locked_at=None,
                    last_error_code=None,
                )
            )

    async def release_for_retry(self, event_id: UUID, delay: float, code: str) -> None:
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(OrderOutboxRecord)
                .where(
                    OrderOutboxRecord.event_id == event_id,
                    OrderOutboxRecord.status == "pending",
                )
                .values(
                    available_at=now + timedelta(seconds=delay),
                    locked_at=None,
                    last_error_code=code,
                )
            )


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.carts: SqlAlchemyCartRepository

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.carts = SqlAlchemyCartRepository(self._session)
        self.orders = SqlAlchemyOrderRepository(self._session)
        self.outbox = SqlAlchemyOrderOutboxRepository(self._session)
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
