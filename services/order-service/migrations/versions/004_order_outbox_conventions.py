"""Align order outbox indexes with the established event architecture.

Revision ID: 004_order_outbox_conventions
Revises: 003_order_lifecycle
"""

from collections.abc import Sequence

from alembic import op

revision: str = "004_order_outbox_conventions"
down_revision: str | None = "003_order_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_order_outbox_aggregate",
        "order_event_outbox",
        ["aggregate_type", "aggregate_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_outbox_aggregate", table_name="order_event_outbox")
