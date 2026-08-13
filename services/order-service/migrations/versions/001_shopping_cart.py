"""Create customer-owned shopping carts and display-snapshot items.

Revision ID: 001_shopping_cart
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_shopping_cart"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shopping_carts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_identity_subject", sa.String(length=255), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active')", name="ck_shopping_carts_status"),
        sa.CheckConstraint("version >= 1", name="ck_shopping_carts_version_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_shopping_carts_active_customer_currency",
        "shopping_carts",
        ["customer_identity_subject", "currency_code"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cart_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("display_sku", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("display_unit_price", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("display_currency_code", sa.String(length=3), nullable=False),
        sa.Column("display_quantity_available", sa.Integer(), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 1 AND quantity <= 1000", name="ck_cart_items_quantity"),
        sa.CheckConstraint("display_unit_price > 0", name="ck_cart_items_display_price_positive"),
        sa.ForeignKeyConstraint(["cart_id"], ["shopping_carts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),
    )
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])


def downgrade() -> None:
    op.drop_index("ix_cart_items_cart_id", table_name="cart_items")
    op.drop_table("cart_items")
    op.drop_index("uq_shopping_carts_active_customer_currency", table_name="shopping_carts")
    op.drop_table("shopping_carts")
