"""Private SQLAlchemy records for shopping-cart persistence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.models import CartStatus, CheckoutAttemptStatus, OrderStatus, utc_now


class Base(DeclarativeBase):
    """Order database metadata root."""


class ShoppingCartRecord(Base):
    __tablename__ = "shopping_carts"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'checked_out')", name="ck_shopping_carts_status"),
        CheckConstraint("version >= 1", name="ck_shopping_carts_version_positive"),
        Index(
            "uq_shopping_carts_active_customer_currency",
            "customer_identity_subject",
            "currency_code",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    customer_identity_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=CartStatus.ACTIVE.value)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class CartItemRecord(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint("quantity >= 1 AND quantity <= 1000", name="ck_cart_items_quantity"),
        CheckConstraint("display_unit_price > 0", name="ck_cart_items_display_price_positive"),
        UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),
        Index("ix_cart_items_cart_id", "cart_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    cart_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("shopping_carts.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    display_sku: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_unit_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    display_currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    display_quantity_available: Mapped[int | None] = mapped_column(Integer)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class OrderRecord(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("order_number", name="uq_orders_order_number"),
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'PROCESSING', 'FULFILLED', "
            "'CANCELLED', 'FAILED')",
            name="ck_orders_status",
        ),
        CheckConstraint("subtotal >= 0 AND total >= 0", name="ck_orders_totals_non_negative"),
        Index("ix_orders_customer_created", "customer_identity_subject", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    order_number: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_identity_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    source_cart_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("shopping_carts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=OrderStatus.CONFIRMED.value
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderItemRecord(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price > 0 AND line_total > 0", name="ck_order_items_money_positive"),
        UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        UniqueConstraint("reservation_id", name="uq_order_items_reservation"),
        Index("ix_order_items_order_id", "order_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    reservation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderStatusHistoryRecord(Base):
    __tablename__ = "order_status_history"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderAuditEventRecord(Base):
    __tablename__ = "order_audit_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    safe_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CheckoutAttemptRecord(Base):
    __tablename__ = "checkout_attempts"
    __table_args__ = (
        UniqueConstraint(
            "customer_identity_subject",
            "idempotency_key",
            name="uq_checkout_attempts_customer_key",
        ),
        CheckConstraint(
            "status IN ('PROCESSING', 'CONFIRMED', 'FAILED', 'COMPENSATION_REQUIRED')",
            name="ck_checkout_attempts_status",
        ),
        Index("ix_checkout_attempts_status_updated", "status", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    customer_identity_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_cart_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_cart_version: Mapped[int] = mapped_column(Integer, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reservation_plan: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CheckoutAttemptStatus.PROCESSING.value
    )
    order_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT")
    )
    reservation_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    unresolved_reservations: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    failure_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderOutboxRecord(Base):
    __tablename__ = "order_event_outbox"
    __table_args__ = (
        CheckConstraint("event_version > 0", name="ck_order_outbox_version_positive"),
        CheckConstraint("status IN ('pending', 'published')", name="ck_order_outbox_status"),
        Index("ix_order_outbox_dispatch", "status", "available_at", "occurred_at"),
    )

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    producer: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
