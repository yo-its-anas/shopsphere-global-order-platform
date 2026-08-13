"""Static SQLAlchemy persistence contract tests independent of a test driver."""

from sqlalchemy import Numeric

from app.infrastructure.orm_models import (
    DomainEventOutboxRecord,
    InventoryItemRecord,
    InventoryMovementRecord,
    ProductCategoryRecord,
    ProductPriceRecord,
    ProductRecord,
)


def test_monetary_amount_uses_fixed_precision_numeric() -> None:
    amount_type = ProductPriceRecord.__table__.c.amount.type

    assert isinstance(amount_type, Numeric)
    assert amount_type.precision == 19
    assert amount_type.scale == 4


def test_database_contract_contains_governed_uniqueness_and_lifecycle_constraints() -> None:
    product_constraints = {constraint.name for constraint in ProductRecord.__table__.constraints}
    category_constraints = {
        constraint.name for constraint in ProductCategoryRecord.__table__.constraints
    }
    price_indexes = {index.name for index in ProductPriceRecord.__table__.indexes}

    assert "uq_products_sku" in product_constraints
    assert "ck_products_status" in product_constraints
    assert "uq_product_categories_slug" in category_constraints
    assert "uq_product_prices_active_currency" in price_indexes


def test_inventory_database_contract_enforces_balance_and_history_constraints() -> None:
    item_constraints = {constraint.name for constraint in InventoryItemRecord.__table__.constraints}
    movement_constraints = {
        constraint.name for constraint in InventoryMovementRecord.__table__.constraints
    }

    assert "uq_inventory_product_location" in item_constraints
    assert "ck_inventory_on_hand_non_negative" in item_constraints
    assert "ck_inventory_reserved_non_negative" in item_constraints
    assert "ck_inventory_reserved_within_on_hand" in item_constraints
    assert "ck_inventory_version_positive" in item_constraints
    assert "uq_inventory_movements_idempotency_key" in movement_constraints
    assert "ck_inventory_movements_type" in movement_constraints
    assert "ck_movements_result_reserved_within_on_hand" in movement_constraints


def test_outbox_contract_has_stable_identity_and_dispatch_indexes() -> None:
    constraints = {constraint.name for constraint in DomainEventOutboxRecord.__table__.constraints}
    indexes = {index.name for index in DomainEventOutboxRecord.__table__.indexes}

    assert "ck_outbox_event_version_positive" in constraints
    assert "ck_outbox_status" in constraints
    assert "ix_outbox_dispatch" in indexes
    assert "ix_outbox_aggregate" in indexes
