"""Add idempotent order checkout, audit, history, and transactional outbox.

Revision ID: 002_order_checkout
Revises: 001_shopping_cart
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_order_checkout"
down_revision: str | None = "001_shopping_cart"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_shopping_carts_status", "shopping_carts", type_="check")
    op.create_check_constraint(
        "ck_shopping_carts_status",
        "shopping_carts",
        "status IN ('active', 'checked_out')",
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(40), nullable=False),
        sa.Column("customer_identity_subject", sa.String(255), nullable=False),
        sa.Column("source_cart_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("subtotal", sa.Numeric(19, 4), nullable=False),
        sa.Column("total", sa.Numeric(19, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('CONFIRMED')", name="ck_orders_status"),
        sa.CheckConstraint("subtotal >= 0 AND total >= 0", name="ck_orders_totals_non_negative"),
        sa.ForeignKeyConstraint(["source_cart_id"], ["shopping_carts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number", name="uq_orders_order_number"),
    )
    op.create_index(
        "ix_orders_customer_created", "orders", ["customer_identity_subject", "created_at"]
    )
    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("line_total", sa.Numeric(19, 4), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint(
            "unit_price > 0 AND line_total > 0", name="ck_order_items_money_positive"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        sa.UniqueConstraint("reservation_id", name="uq_order_items_reservation"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("actor_subject", sa.String(255), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "order_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("actor_subject", sa.String(255), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "checkout_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_identity_subject", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("source_cart_id", sa.Uuid(), nullable=False),
        sa.Column("source_cart_version", sa.Integer(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("reservation_plan", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("reservation_ids", sa.JSON(), nullable=False),
        sa.Column("unresolved_reservations", sa.JSON(), nullable=False),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'CONFIRMED', 'FAILED', 'COMPENSATION_REQUIRED')",
            name="ck_checkout_attempts_status",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_identity_subject", "idempotency_key", name="uq_checkout_attempts_customer_key"
        ),
    )
    op.create_index(
        "ix_checkout_attempts_status_updated", "checkout_attempts", ["status", "updated_at"]
    )
    op.create_table(
        "order_event_outbox",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("producer", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.CheckConstraint("event_version > 0", name="ck_order_outbox_version_positive"),
        sa.CheckConstraint("status IN ('pending', 'published')", name="ck_order_outbox_status"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_order_outbox_dispatch",
        "order_event_outbox",
        ["status", "available_at", "occurred_at"],
    )
    op.execute("""
        CREATE FUNCTION reject_order_evidence_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'order evidence is append-only' USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql;
        """)
    for table_name in ("order_items", "order_status_history", "order_audit_events"):
        op.execute(f"""
            CREATE TRIGGER {table_name}_append_only
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION reject_order_evidence_mutation();
            """)


def downgrade() -> None:
    for table_name in ("order_items", "order_status_history", "order_audit_events"):
        op.execute(f"DROP TRIGGER {table_name}_append_only ON {table_name}")
    op.execute("DROP FUNCTION reject_order_evidence_mutation()")
    op.drop_index("ix_order_outbox_dispatch", table_name="order_event_outbox")
    op.drop_table("order_event_outbox")
    op.drop_index("ix_checkout_attempts_status_updated", table_name="checkout_attempts")
    op.drop_table("checkout_attempts")
    op.drop_table("order_audit_events")
    op.drop_table("order_status_history")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_customer_created", table_name="orders")
    op.drop_table("orders")
    op.drop_constraint("ck_shopping_carts_status", "shopping_carts", type_="check")
    op.create_check_constraint("ck_shopping_carts_status", "shopping_carts", "status IN ('active')")
