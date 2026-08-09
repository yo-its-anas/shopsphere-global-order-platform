"""Create customer profiles, addresses, and append-only audit events.

Revision ID: 001_customer_accounts
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_customer_accounts"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_provider_subject", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("account_status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "account_status IN ('active', 'suspended', 'closed')",
            name="ck_customer_profiles_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identity_provider_subject", name="uq_customer_profiles_idp_subject"),
    )
    op.create_table(
        "customer_addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("recipient_name", sa.String(length=200), nullable=False),
        sa.Column("line1", sa.String(length=200), nullable=False),
        sa.Column("line2", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customer_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_addresses_customer_id", "customer_addresses", ["customer_id"])
    op.create_index(
        "uq_customer_addresses_one_default",
        "customer_addresses",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
        sqlite_where=sa.text("is_default = 1"),
    )
    op.create_table(
        "customer_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customer_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_audit_events_customer_time",
        "customer_audit_events",
        ["customer_id", "occurred_at"],
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION shopsphere_reject_customer_audit_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'customer audit events are append-only';
            END;
            $$ LANGUAGE plpgsql
            """)
        op.execute("""
            CREATE TRIGGER trg_customer_audit_events_append_only
            BEFORE UPDATE OR DELETE ON customer_audit_events
            FOR EACH ROW EXECUTE FUNCTION shopsphere_reject_customer_audit_mutation()
            """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_customer_audit_events_append_only "
            "ON customer_audit_events"
        )
        op.execute("DROP FUNCTION IF EXISTS shopsphere_reject_customer_audit_mutation()")
    op.drop_index("ix_customer_audit_events_customer_time", table_name="customer_audit_events")
    op.drop_table("customer_audit_events")
    op.drop_index("uq_customer_addresses_one_default", table_name="customer_addresses")
    op.drop_index("ix_customer_addresses_customer_id", table_name="customer_addresses")
    op.drop_table("customer_addresses")
    op.drop_table("customer_profiles")
