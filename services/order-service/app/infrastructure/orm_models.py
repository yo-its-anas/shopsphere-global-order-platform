"""Private SQLAlchemy records for shopping-cart persistence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
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

from app.domain.models import CartStatus, utc_now


class Base(DeclarativeBase):
    """Order database metadata root."""


class ShoppingCartRecord(Base):
    __tablename__ = "shopping_carts"
    __table_args__ = (
        CheckConstraint("status IN ('active')", name="ck_shopping_carts_status"),
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
