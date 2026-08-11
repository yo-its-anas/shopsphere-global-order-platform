"""Private SQLAlchemy persistence models for Product Catalogue."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.models import InventoryMovementType, ProductStatus, utc_now


class Base(DeclarativeBase):
    """Catalogue database metadata root."""


class ProductCategoryRecord(Base):
    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_product_categories_slug"),
        CheckConstraint("length(name) > 0", name="ck_product_categories_name_not_empty"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("product_categories.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ProductRecord(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_products_sku"),
        CheckConstraint(
            "status IN ('draft', 'active', 'inactive', 'discontinued')",
            name="ck_products_status",
        ),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_status_searchable", "status", "is_searchable"),
        Index("ix_products_name", "name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("product_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProductStatus.DRAFT.value
    )
    is_searchable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ProductPriceRecord(Base):
    __tablename__ = "product_prices"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_product_prices_amount_positive"),
        CheckConstraint("length(currency_code) = 3", name="ck_product_prices_currency_length"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_product_prices_effective_interval",
        ),
        Index("ix_product_prices_product_id", "product_id"),
        Index(
            "uq_product_prices_active_currency",
            "product_id",
            "currency_code",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class InventoryItemRecord(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("product_id", "location_code", name="uq_inventory_product_location"),
        CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_on_hand_non_negative"),
        CheckConstraint("quantity_reserved >= 0", name="ck_inventory_reserved_non_negative"),
        CheckConstraint(
            "quantity_reserved <= quantity_on_hand", name="ck_inventory_reserved_within_on_hand"
        ),
        CheckConstraint("reorder_threshold >= 0", name="ck_inventory_reorder_non_negative"),
        CheckConstraint("version >= 1", name="ck_inventory_version_positive"),
        Index("ix_inventory_items_product_id", "product_id"),
        Index("ix_inventory_items_location", "location_code"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    location_code: Mapped[str] = mapped_column(String(40), nullable=False, default="PRIMARY")
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class InventoryMovementRecord(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_inventory_movements_idempotency_key"),
        CheckConstraint(
            "movement_type IN ('INITIAL_STOCK', 'STOCK_RECEIPT', 'MANUAL_ADJUSTMENT', "
            "'DAMAGE', 'CORRECTION', 'RESERVATION', 'RELEASE', 'FULFILMENT')",
            name="ck_inventory_movements_type",
        ),
        CheckConstraint(
            "quantity_delta <> 0 OR movement_type = 'INITIAL_STOCK'",
            name="ck_inventory_movements_non_zero",
        ),
        CheckConstraint(
            "resulting_quantity_on_hand >= 0", name="ck_movements_result_on_hand_non_negative"
        ),
        CheckConstraint(
            "resulting_quantity_reserved >= 0", name="ck_movements_result_reserved_non_negative"
        ),
        CheckConstraint(
            "resulting_quantity_reserved <= resulting_quantity_on_hand",
            name="ck_movements_result_reserved_within_on_hand",
        ),
        Index("ix_inventory_movements_item_time", "inventory_item_id", "occurred_at"),
        Index("ix_inventory_movements_product_time", "product_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    inventory_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    movement_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=InventoryMovementType.MANUAL_ADJUSTMENT.value
    )
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    previous_quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    resulting_quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False)
    resulting_quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class DomainEventOutboxRecord(Base):
    __tablename__ = "domain_event_outbox"
    __table_args__ = (
        CheckConstraint("event_version > 0", name="ck_outbox_event_version_positive"),
        CheckConstraint("status IN ('pending', 'published')", name="ck_outbox_status"),
        Index("ix_outbox_dispatch", "status", "available_at", "occurred_at"),
        Index("ix_outbox_aggregate", "aggregate_type", "aggregate_id", "occurred_at"),
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
