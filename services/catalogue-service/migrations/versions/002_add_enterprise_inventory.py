"""Add transactional inventory balances and append-only movements.

Revision ID: 002_enterprise_inventory
Revises: 001_product_catalogue
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_enterprise_inventory"
down_revision: str | None = "001_product_catalogue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("location_code", sa.String(length=40), nullable=False),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=False),
        sa.Column("quantity_reserved", sa.Integer(), nullable=False),
        sa.Column("reorder_threshold", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_on_hand_non_negative"),
        sa.CheckConstraint("quantity_reserved >= 0", name="ck_inventory_reserved_non_negative"),
        sa.CheckConstraint(
            "quantity_reserved <= quantity_on_hand",
            name="ck_inventory_reserved_within_on_hand",
        ),
        sa.CheckConstraint("reorder_threshold >= 0", name="ck_inventory_reorder_non_negative"),
        sa.CheckConstraint("version >= 1", name="ck_inventory_version_positive"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "location_code", name="uq_inventory_product_location"),
    )
    op.create_index("ix_inventory_items_location", "inventory_items", ["location_code"])
    op.create_index("ix_inventory_items_product_id", "inventory_items", ["product_id"])

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("reserved_delta", sa.Integer(), nullable=False),
        sa.Column("previous_quantity_on_hand", sa.Integer(), nullable=False),
        sa.Column("resulting_quantity_on_hand", sa.Integer(), nullable=False),
        sa.Column("previous_quantity_reserved", sa.Integer(), nullable=False),
        sa.Column("resulting_quantity_reserved", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "movement_type IN ('INITIAL_STOCK', 'STOCK_RECEIPT', 'MANUAL_ADJUSTMENT', "
            "'DAMAGE', 'CORRECTION', 'RESERVATION', 'RELEASE', 'FULFILMENT')",
            name="ck_inventory_movements_type",
        ),
        sa.CheckConstraint(
            "quantity_delta <> 0 OR movement_type = 'INITIAL_STOCK'",
            name="ck_inventory_movements_non_zero",
        ),
        sa.CheckConstraint(
            "resulting_quantity_on_hand >= 0",
            name="ck_movements_result_on_hand_non_negative",
        ),
        sa.CheckConstraint(
            "resulting_quantity_reserved >= 0",
            name="ck_movements_result_reserved_non_negative",
        ),
        sa.CheckConstraint(
            "resulting_quantity_reserved <= resulting_quantity_on_hand",
            name="ck_movements_result_reserved_within_on_hand",
        ),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_inventory_movements_idempotency_key"),
    )
    op.create_index(
        "ix_inventory_movements_item_time",
        "inventory_movements",
        ["inventory_item_id", "occurred_at"],
    )
    op.create_index(
        "ix_inventory_movements_product_time",
        "inventory_movements",
        ["product_id", "occurred_at"],
    )
    op.execute("""
        CREATE FUNCTION reject_inventory_movement_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'inventory movements are append-only' USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE TRIGGER inventory_movements_append_only
        BEFORE UPDATE OR DELETE ON inventory_movements
        FOR EACH ROW EXECUTE FUNCTION reject_inventory_movement_mutation();
        """)


def downgrade() -> None:
    op.execute("DROP TRIGGER inventory_movements_append_only ON inventory_movements")
    op.execute("DROP FUNCTION reject_inventory_movement_mutation()")
    op.drop_index("ix_inventory_movements_product_time", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_item_time", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index("ix_inventory_items_product_id", table_name="inventory_items")
    op.drop_index("ix_inventory_items_location", table_name="inventory_items")
    op.drop_table("inventory_items")
