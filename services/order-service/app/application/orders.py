"""Actor-scoped order queries and controlled lifecycle commands."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from uuid import UUID

from app.core.errors import AuthorizationError, InvalidOperationError, ResourceNotFoundError
from app.core.security import Principal, Role
from app.domain.events import order_cancelled, order_status_changed
from app.domain.models import (
    Order,
    OrderAuditEvent,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    utc_now,
)
from app.domain.repositories import CatalogueProductProvider, UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
ADMIN_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CONFIRMED: frozenset({OrderStatus.PROCESSING}),
    OrderStatus.PROCESSING: frozenset({OrderStatus.FULFILLED}),
}
CANCELLABLE = frozenset({OrderStatus.CONFIRMED, OrderStatus.PROCESSING})


class OrderService:
    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        catalogue: CatalogueProductProvider,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._catalogue = catalogue

    async def list_orders(
        self,
        actor: Principal,
        *,
        customer_subject: str | None,
        status: OrderStatus | None,
        offset: int,
        limit: int,
        ascending: bool,
        administrative: bool,
    ) -> tuple[Sequence[Order], int]:
        subject = self._query_subject(actor, customer_subject, administrative)
        async with self._unit_of_work_factory() as work:
            return await work.orders.list_orders(
                customer_subject=subject,
                status=status.value if status else None,
                offset=offset,
                limit=limit,
                ascending=ascending,
            )

    async def detail(
        self, actor: Principal, order_id: UUID, *, administrative: bool
    ) -> tuple[Order, Sequence[OrderItem]]:
        async with self._unit_of_work_factory() as work:
            order = await work.orders.get_order(order_id)
            self._authorize_read(actor, order, administrative)
            return order, await work.orders.list_order_items(order.id)

    async def history(
        self, actor: Principal, order_id: UUID, *, administrative: bool
    ) -> tuple[Order, Sequence[OrderStatusHistory]]:
        async with self._unit_of_work_factory() as work:
            order = await work.orders.get_order(order_id)
            self._authorize_read(actor, order, administrative)
            return order, await work.orders.list_status_history(order.id)

    async def audit(
        self,
        actor: Principal,
        order_id: UUID,
        *,
        offset: int,
        limit: int,
        administrative: bool,
    ) -> tuple[Order, Sequence[OrderAuditEvent], int]:
        async with self._unit_of_work_factory() as work:
            order = await work.orders.get_order(order_id)
            self._authorize_read(actor, order, administrative)
            events, total = await work.orders.list_audit_events(
                order.id, offset=offset, limit=limit
            )
            return order, events, total

    async def transition(
        self,
        actor: Principal,
        order_id: UUID,
        target: OrderStatus,
        correlation_id: str,
    ) -> Order:
        if not actor.has_role(Role.OPERATIONS_ADMIN):
            raise AuthorizationError
        async with self._unit_of_work_factory() as work:
            order = await work.orders.get_order(order_id, for_update=True)
            if order is None:
                raise ResourceNotFoundError
            if order.status is target:
                return order
            if target not in ADMIN_TRANSITIONS.get(order.status, frozenset()):
                raise InvalidOperationError
            if target is OrderStatus.FULFILLED:
                for item in await work.orders.list_order_items(order.id):
                    await self._catalogue.consume_inventory(item.reservation_id, correlation_id)
            return await self._record_transition(work, order, target, actor, correlation_id)

    async def cancel(
        self,
        actor: Principal,
        order_id: UUID,
        correlation_id: str,
        *,
        administrative: bool,
    ) -> Order:
        if administrative:
            if not actor.has_role(Role.OPERATIONS_ADMIN):
                raise AuthorizationError
        elif not actor.has_role(Role.CUSTOMER):
            raise AuthorizationError
        async with self._unit_of_work_factory() as work:
            order = await work.orders.get_order(order_id, for_update=True)
            if order is None:
                raise ResourceNotFoundError
            if not administrative and order.customer_identity_subject != actor.subject:
                raise ResourceNotFoundError
            if order.status is OrderStatus.CANCELLED:
                return order
            if order.status not in CANCELLABLE:
                raise InvalidOperationError
            items = await work.orders.list_order_items(order.id)
            for item in items:
                await self._catalogue.release_inventory(item.reservation_id, correlation_id)
            cancelled = await self._record_transition(
                work, order, OrderStatus.CANCELLED, actor, correlation_id, commit=False
            )
            work.orders.add_audit_event(
                OrderAuditEvent(
                    order_id=order.id,
                    action="inventory.reservations_released",
                    actor_subject=actor.subject,
                    correlation_id=correlation_id,
                    metadata={"reservation_count": len(items)},
                )
            )
            work.outbox.add(order_cancelled(cancelled, correlation_id))
            await work.flush()
            await work.commit()
            return cancelled

    async def _record_transition(
        self,
        work: UnitOfWork,
        order: Order,
        target: OrderStatus,
        actor: Principal,
        correlation_id: str,
        *,
        commit: bool = True,
    ) -> Order:
        previous = order.status
        changed = replace(order, status=target, updated_at=utc_now())
        await work.orders.update_order(changed)
        work.orders.add_status_history(
            OrderStatusHistory(
                order_id=order.id,
                status=target,
                actor_subject=actor.subject,
                correlation_id=correlation_id,
            )
        )
        work.orders.add_audit_event(
            OrderAuditEvent(
                order_id=order.id,
                action="order.status_changed",
                actor_subject=actor.subject,
                correlation_id=correlation_id,
                metadata={"previous_status": previous.value, "status": target.value},
            )
        )
        work.outbox.add(order_status_changed(changed, previous.value, correlation_id))
        if commit:
            await work.flush()
            await work.commit()
        return changed

    @staticmethod
    def _authorize_read(actor: Principal, order: Order | None, administrative: bool) -> None:
        if order is None:
            raise ResourceNotFoundError
        if administrative:
            if not (actor.has_role(Role.SUPPORT) or actor.has_role(Role.OPERATIONS_ADMIN)):
                raise AuthorizationError
        elif not actor.has_role(Role.CUSTOMER) or order.customer_identity_subject != actor.subject:
            raise ResourceNotFoundError

    @staticmethod
    def _query_subject(
        actor: Principal, customer_subject: str | None, administrative: bool
    ) -> str | None:
        if administrative:
            if not (actor.has_role(Role.SUPPORT) or actor.has_role(Role.OPERATIONS_ADMIN)):
                raise AuthorizationError
            return customer_subject
        if not actor.has_role(Role.CUSTOMER):
            raise AuthorizationError
        return actor.subject
