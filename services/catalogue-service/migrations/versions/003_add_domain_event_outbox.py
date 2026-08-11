"""Add recoverable transactional domain-event outbox.

Revision ID: 003_domain_event_outbox
Revises: 002_enterprise_inventory
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_domain_event_outbox"
down_revision: str | None = "002_enterprise_inventory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "domain_event_outbox",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("producer", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.CheckConstraint("event_version > 0", name="ck_outbox_event_version_positive"),
        sa.CheckConstraint("status IN ('pending', 'published')", name="ck_outbox_status"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_outbox_dispatch",
        "domain_event_outbox",
        ["status", "available_at", "occurred_at"],
    )
    op.create_index(
        "ix_outbox_aggregate",
        "domain_event_outbox",
        ["aggregate_type", "aggregate_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_aggregate", table_name="domain_event_outbox")
    op.drop_index("ix_outbox_dispatch", table_name="domain_event_outbox")
    op.drop_table("domain_event_outbox")
