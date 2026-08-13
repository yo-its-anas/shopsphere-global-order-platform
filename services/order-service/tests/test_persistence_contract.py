"""Outbox schema and database transaction-boundary contract tests."""

from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.events import DomainEvent, order_created
from app.domain.models import Order, ShoppingCart
from app.infrastructure.orm_models import (
    Base,
    OrderOutboxRecord,
    OrderRecord,
    ShoppingCartRecord,
)


def test_outbox_contract_has_stable_identity_and_dispatch_indexes() -> None:
    constraints = {constraint.name for constraint in OrderOutboxRecord.__table__.constraints}
    indexes = {index.name for index in OrderOutboxRecord.__table__.indexes}

    assert "ck_order_outbox_version_positive" in constraints
    assert "ck_order_outbox_status" in constraints
    assert "ix_order_outbox_dispatch" in indexes
    assert "ix_order_outbox_aggregate" in indexes


def _records(cart: ShoppingCart, order: Order, event: DomainEvent) -> tuple[Any, Any, Any]:
    return (
        ShoppingCartRecord(
            id=cart.id,
            customer_identity_subject=cart.customer_identity_subject,
            currency_code=cart.currency_code,
            status=cart.status.value,
            version=cart.version,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
        ),
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
        ),
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
        ),
    )


def test_order_and_outbox_commit_or_roll_back_atomically() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    cart = ShoppingCart(customer_identity_subject="atomic-customer", currency_code="USD")
    order = Order(
        customer_identity_subject=cart.customer_identity_subject,
        source_cart_id=cart.id,
        order_number="SS-ATOMIC-ONE",
        currency_code="USD",
        subtotal=Decimal("10.0000"),
        total=Decimal("10.0000"),
    )
    event = order_created(order, 1, "atomic-correlation")
    with Session(engine) as session:
        session.add_all(_records(cart, order, event))
        session.commit()

    failed_cart = ShoppingCart(customer_identity_subject="rollback-customer", currency_code="USD")
    failed_order = Order(
        customer_identity_subject=failed_cart.customer_identity_subject,
        source_cart_id=failed_cart.id,
        order_number="SS-ATOMIC-ROLLBACK",
        currency_code="USD",
        subtotal=Decimal("5.0000"),
        total=Decimal("5.0000"),
    )
    with Session(engine) as session:
        try:
            session.add_all(_records(failed_cart, failed_order, event))
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Expected duplicate event identity to reject the transaction")

    with Session(engine) as session:
        order_count = session.scalar(select(func.count()).select_from(OrderRecord))
        event_count = session.scalar(select(func.count()).select_from(OrderOutboxRecord))
        rolled_back = session.scalar(select(OrderRecord).where(OrderRecord.id == failed_order.id))
    assert order_count == 1
    assert event_count == 1
    assert rolled_back is None
