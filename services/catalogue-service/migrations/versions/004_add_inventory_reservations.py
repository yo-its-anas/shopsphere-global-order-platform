"""Add controlled inventory reservations and reservation movement semantics.

Revision ID: 004_inventory_reservations
Revises: 003_domain_event_outbox
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_inventory_reservations"
down_revision: str | None = "003_domain_event_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_inventory_movements_non_zero",
        "inventory_movements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_inventory_movements_non_zero",
        "inventory_movements",
        "quantity_delta <> 0 OR reserved_delta <> 0 OR movement_type = 'INITIAL_STOCK'",
    )
    op.create_table(
        "inventory_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_reservations_quantity_positive"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'CONSUMED', 'RELEASED')",
            name="ck_inventory_reservations_status",
        ),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_reference", name="uq_inventory_reservations_external_ref"),
    )
    op.create_index(
        "ix_inventory_reservations_product_status",
        "inventory_reservations",
        ["product_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_reservations_product_status",
        table_name="inventory_reservations",
    )
    op.drop_table("inventory_reservations")
    op.drop_constraint(
        "ck_inventory_movements_non_zero",
        "inventory_movements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_inventory_movements_non_zero",
        "inventory_movements",
        "quantity_delta <> 0 OR movement_type = 'INITIAL_STOCK'",
    )
