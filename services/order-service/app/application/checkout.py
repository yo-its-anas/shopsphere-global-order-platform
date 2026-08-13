"""Idempotent checkout Saga orchestration."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import (
    ApplicationError,
    ConflictError,
    DependencyUnavailableError,
    InvalidOperationError,
)
from app.domain.events import order_confirmed, order_created
from app.domain.models import (
    CartItem,
    CartStatus,
    CatalogueProductSnapshot,
    CheckoutAttempt,
    CheckoutAttemptStatus,
    InventoryReservationReceipt,
    Order,
    OrderAuditEvent,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    ShoppingCart,
    utc_now,
)
from app.domain.repositories import CatalogueProductProvider, UnitOfWork

logger = logging.getLogger(__name__)
UnitOfWorkFactory = Callable[[], UnitOfWork]
MONEY_QUANTUM = Decimal("0.0001")


class CheckoutService:
    """Coordinates catalogue validation, reservations, and local atomic persistence."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        catalogue: CatalogueProductProvider,
        currency_code: str,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._catalogue = catalogue
        self._currency_code = currency_code

    async def checkout(
        self,
        customer_subject: str,
        access_token: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> tuple[Order, Sequence[OrderItem]]:
        existing = await self._attempt(customer_subject, idempotency_key)
        if existing is not None:
            return await self._resolve_retry(existing, customer_subject)

        cart, cart_items = await self._active_cart(customer_subject)
        if not cart_items:
            raise InvalidOperationError
        fingerprint = self._fingerprint(cart, cart_items)
        attempt = CheckoutAttempt(
            customer_identity_subject=customer_subject,
            idempotency_key=idempotency_key,
            source_cart_id=cart.id,
            source_cart_version=cart.version,
            request_fingerprint=fingerprint,
            reservation_plan=[],
        )
        attempt.reservation_plan = [
            {
                "product_id": str(item.product_id),
                "quantity": item.quantity,
                "external_reference": f"checkout:{attempt.id}:{item.product_id}",
            }
            for item in sorted(cart_items, key=lambda value: str(value.product_id))
        ]
        try:
            async with self._unit_of_work_factory() as work:
                work.orders.add_checkout_attempt(attempt)
                await work.flush()
                await work.commit()
        except IntegrityError:
            existing = await self._attempt(customer_subject, idempotency_key)
            if existing is None:
                raise ConflictError from None
            return await self._resolve_retry(existing, customer_subject)

        logger.info(
            "checkout_initiated",
            extra={
                "event": "checkout_initiated",
                "checkout_attempt_id": str(attempt.id),
                "cart_id": str(cart.id),
                "actor_subject": customer_subject,
                "correlation_id": correlation_id,
            },
        )
        receipts: list[InventoryReservationReceipt] = []
        try:
            snapshots = await self._authoritative_snapshots(
                cart_items, access_token, correlation_id
            )
            for planned in attempt.reservation_plan:
                receipt = await self._catalogue.reserve_inventory(
                    UUID(planned["product_id"]),
                    int(planned["quantity"]),
                    str(planned["external_reference"]),
                    correlation_id,
                )
                receipts.append(receipt)
                await self._record_receipts(attempt, receipts)
            return await self._persist_order(
                attempt,
                cart,
                cart_items,
                snapshots,
                receipts,
                customer_subject,
                correlation_id,
            )
        except ApplicationError as exc:
            await self._compensate(attempt, receipts, correlation_id, exc.code)
            raise
        except Exception as exc:
            recovered = await self._recover_confirmed(attempt)
            if recovered is not None:
                return recovered
            await self._compensate(attempt, receipts, correlation_id, "order_persistence_failed")
            raise DependencyUnavailableError from exc

    async def _authoritative_snapshots(
        self, items: Sequence[CartItem], access_token: str, correlation_id: str
    ) -> dict[UUID, CatalogueProductSnapshot]:
        snapshots: dict[UUID, CatalogueProductSnapshot] = {}
        for item in sorted(items, key=lambda value: str(value.product_id)):
            snapshot = await self._catalogue.get_product_snapshot(
                item.product_id, self._currency_code, access_token, correlation_id
            )
            if (
                snapshot.quantity_available is not None
                and snapshot.quantity_available < item.quantity
            ):
                from app.core.errors import ProductUnavailableError

                raise ProductUnavailableError
            snapshots[item.product_id] = snapshot
        return snapshots

    async def _persist_order(
        self,
        attempt: CheckoutAttempt,
        cart: ShoppingCart,
        cart_items: Sequence[CartItem],
        snapshots: dict[UUID, CatalogueProductSnapshot],
        receipts: Sequence[InventoryReservationReceipt],
        customer_subject: str,
        correlation_id: str,
    ) -> tuple[Order, Sequence[OrderItem]]:
        receipt_by_product = {receipt.product_id: receipt for receipt in receipts}
        now = utc_now()
        order_id = UUID(int=attempt.id.int ^ cart.id.int)
        order_items: list[OrderItem] = []
        for item in cart_items:
            unit_price = self._money(snapshots[item.product_id].unit_price)
            order_items.append(
                OrderItem(
                    order_id=order_id,
                    product_id=item.product_id,
                    sku=snapshots[item.product_id].sku,
                    product_name=snapshots[item.product_id].name,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    currency_code=self._currency_code,
                    line_total=self._money(unit_price * item.quantity),
                    reservation_id=receipt_by_product[item.product_id].reservation_id,
                )
            )
        subtotal = self._money(sum((item.line_total for item in order_items), Decimal("0")))
        order = Order(
            id=order_id,
            customer_identity_subject=customer_subject,
            source_cart_id=cart.id,
            order_number=f"SS-{now:%Y%m%d}-{order_id.hex[:12].upper()}",
            currency_code=self._currency_code,
            subtotal=subtotal,
            total=subtotal,
            created_at=now,
            updated_at=now,
        )
        async with self._unit_of_work_factory() as work:
            locked_cart = await work.carts.get_cart_by_id(cart.id, for_update=True)
            current_items = await work.carts.list_items(cart.id)
            if (
                locked_cart is None
                or locked_cart.customer_identity_subject != customer_subject
                or locked_cart.status is not CartStatus.ACTIVE
                or locked_cart.version != attempt.source_cart_version
                or self._fingerprint(locked_cart, current_items) != attempt.request_fingerprint
            ):
                raise ConflictError
            current_attempt = await work.orders.get_checkout_attempt(
                customer_subject, attempt.idempotency_key, for_update=True
            )
            if (
                current_attempt is None
                or current_attempt.status is not CheckoutAttemptStatus.PROCESSING
            ):
                raise ConflictError
            work.orders.add_order(order)
            for order_item in order_items:
                work.orders.add_order_item(order_item)
            work.orders.add_status_history(
                OrderStatusHistory(
                    order_id=order.id,
                    status=OrderStatus.CONFIRMED,
                    actor_subject=customer_subject,
                    correlation_id=correlation_id,
                )
            )
            for action, metadata in (
                ("checkout.initiated", {"source_cart_id": str(cart.id)}),
                ("inventory.reserved", {"reservation_count": len(receipts)}),
                ("order.created", {"item_count": len(order_items)}),
                ("order.confirmed", {"status": order.status.value}),
            ):
                work.orders.add_audit_event(
                    OrderAuditEvent(
                        order_id=order.id,
                        action=action,
                        actor_subject=customer_subject,
                        correlation_id=correlation_id,
                        metadata=metadata,
                    )
                )
            work.outbox.add(order_created(order, len(order_items), correlation_id))
            work.outbox.add(order_confirmed(order, correlation_id))
            if not await work.carts.update_cart(
                replace(
                    locked_cart,
                    status=CartStatus.CHECKED_OUT,
                    version=locked_cart.version + 1,
                    updated_at=now,
                ),
                locked_cart.version,
            ):
                raise ConflictError
            await work.carts.clear_items(cart.id)
            current_attempt.status = CheckoutAttemptStatus.CONFIRMED
            current_attempt.order_id = order.id
            current_attempt.reservation_ids = [str(value.reservation_id) for value in receipts]
            current_attempt.updated_at = now
            await work.orders.update_checkout_attempt(current_attempt)
            await work.flush()
            await work.commit()
        return order, order_items

    async def _compensate(
        self,
        attempt: CheckoutAttempt,
        receipts: Sequence[InventoryReservationReceipt],
        correlation_id: str,
        failure_code: str,
    ) -> None:
        unresolved: list[dict[str, str]] = []
        for receipt in reversed(receipts):
            try:
                await self._catalogue.release_inventory(receipt.reservation_id, correlation_id)
            except Exception:
                unresolved.append(
                    {
                        "reservation_id": str(receipt.reservation_id),
                        "external_reference": receipt.external_reference,
                        "reason": "release_failed",
                    }
                )
        try:
            async with self._unit_of_work_factory() as work:
                current = await work.orders.get_checkout_attempt(
                    attempt.customer_identity_subject, attempt.idempotency_key, for_update=True
                )
                if current is not None and current.status is CheckoutAttemptStatus.PROCESSING:
                    current.status = (
                        CheckoutAttemptStatus.COMPENSATION_REQUIRED
                        if unresolved
                        else CheckoutAttemptStatus.FAILED
                    )
                    current.reservation_ids = [str(value.reservation_id) for value in receipts]
                    current.unresolved_reservations = unresolved
                    current.failure_code = failure_code
                    current.updated_at = utc_now()
                    await work.orders.update_checkout_attempt(current)
                    await work.commit()
        except Exception:
            logger.exception(
                "checkout_reconciliation_evidence_write_failed",
                extra={"event": "checkout_reconciliation_evidence_write_failed"},
            )
        logger.warning(
            "checkout_compensated" if not unresolved else "checkout_compensation_required",
            extra={
                "event": (
                    "checkout_compensated" if not unresolved else "checkout_compensation_required"
                ),
                "checkout_attempt_id": str(attempt.id),
                "released_count": len(receipts) - len(unresolved),
                "unresolved_count": len(unresolved),
                "correlation_id": correlation_id,
            },
        )

    async def _record_receipts(
        self, attempt: CheckoutAttempt, receipts: Sequence[InventoryReservationReceipt]
    ) -> None:
        async with self._unit_of_work_factory() as work:
            current = await work.orders.get_checkout_attempt(
                attempt.customer_identity_subject, attempt.idempotency_key, for_update=True
            )
            if current is None or current.status is not CheckoutAttemptStatus.PROCESSING:
                raise ConflictError
            current.reservation_ids = [str(value.reservation_id) for value in receipts]
            current.updated_at = utc_now()
            await work.orders.update_checkout_attempt(current)
            await work.commit()

    async def _resolve_retry(
        self, attempt: CheckoutAttempt, customer_subject: str
    ) -> tuple[Order, Sequence[OrderItem]]:
        if attempt.status is not CheckoutAttemptStatus.CONFIRMED or attempt.order_id is None:
            raise ConflictError
        async with self._unit_of_work_factory() as work:
            active = await work.carts.get_active_cart(customer_subject, self._currency_code)
            if active is not None and await work.carts.list_items(active.id):
                raise ConflictError
            order = await work.orders.get_order(attempt.order_id)
            if order is None or order.customer_identity_subject != customer_subject:
                raise ConflictError
            return order, await work.orders.list_order_items(order.id)

    async def _recover_confirmed(
        self, attempt: CheckoutAttempt
    ) -> tuple[Order, Sequence[OrderItem]] | None:
        """Resolve an ambiguous local commit before releasing external reservations."""

        try:
            current = await self._attempt(
                attempt.customer_identity_subject, attempt.idempotency_key
            )
            if (
                current is None
                or current.status is not CheckoutAttemptStatus.CONFIRMED
                or current.order_id is None
            ):
                return None
            async with self._unit_of_work_factory() as work:
                order = await work.orders.get_order(current.order_id)
                if order is None:
                    return None
                return order, await work.orders.list_order_items(order.id)
        except Exception:
            return None

    async def _attempt(self, subject: str, key: str) -> CheckoutAttempt | None:
        async with self._unit_of_work_factory() as work:
            return await work.orders.get_checkout_attempt(subject, key)

    async def _active_cart(self, subject: str) -> tuple[ShoppingCart, Sequence[CartItem]]:
        async with self._unit_of_work_factory() as work:
            cart = await work.carts.get_active_cart(subject, self._currency_code)
            if cart is None:
                raise InvalidOperationError
            return cart, await work.carts.list_items(cart.id)

    @staticmethod
    def _fingerprint(cart: ShoppingCart, items: Sequence[CartItem]) -> str:
        value = {
            "cart_id": str(cart.id),
            "cart_version": cart.version,
            "currency_code": cart.currency_code,
            "items": sorted(
                ({"product_id": str(item.product_id), "quantity": item.quantity} for item in items),
                key=lambda item: item["product_id"],
            ),
        }
        return hashlib.sha256(
            json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
