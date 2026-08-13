"""Expand the controlled order lifecycle state constraint.

Revision ID: 003_order_lifecycle
Revises: 002_order_checkout
"""

from collections.abc import Sequence

from alembic import op

revision: str = "003_order_lifecycle"
down_revision: str | None = "002_order_checkout"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_orders_status", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_status",
        "orders",
        "status IN ('PENDING', 'CONFIRMED', 'PROCESSING', 'FULFILLED', " "'CANCELLED', 'FAILED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_orders_status", "orders", type_="check")
    op.create_check_constraint("ck_orders_status", "orders", "status IN ('CONFIRMED')")
