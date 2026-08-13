"""Inventory invariants, movement history, RBAC, statistics, and concurrency tests."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.application.inventory import InventoryService
from app.core.errors import ConflictError, InvalidOperationError
from app.core.security import Principal
from app.domain.inventory import validate_balances
from app.domain.models import InventoryItem, InventoryMovement, InventoryMovementType


def _product(client: Any, auth_headers: Any, suffix: str = "001") -> dict[str, Any]:
    category = client.post(
        "/api/v1/categories",
        headers=auth_headers("operations_admin"),
        json={"name": f"Inventory {suffix}", "slug": f"inventory-{suffix}"},
    )
    assert category.status_code == 201, category.text
    product = client.post(
        "/api/v1/products",
        headers=auth_headers("operations_admin"),
        json={
            "sku": f"INV-{suffix}",
            "name": f"Inventory Product {suffix}",
            "category_id": category.json()["id"],
            "status": "active",
            "is_searchable": True,
        },
    )
    assert product.status_code == 201, product.text
    return product.json()


def _initialize(
    client: Any,
    auth_headers: Any,
    product_id: str,
    *,
    quantity: int = 10,
    threshold: int = 2,
    key: str = "initial-stock-001",
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/inventory/products/{product_id}/initialize",
        headers={**auth_headers("operations_admin"), "X-Request-ID": "inventory-init"},
        json={
            "quantity_on_hand": quantity,
            "reorder_threshold": threshold,
            "reason": "Initial warehouse count",
            "reference": "POC-OPENING",
            "idempotency_key": key,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _adjust(
    client: Any,
    auth_headers: Any,
    product_id: str,
    *,
    movement_type: str,
    delta: int,
    key: str,
    expected_version: int | None = None,
) -> Any:
    body: dict[str, Any] = {
        "movement_type": movement_type,
        "quantity_delta": delta,
        "reason": "Validated stock operation",
        "reference": "TEST-REFERENCE",
        "idempotency_key": key,
    }
    if expected_version is not None:
        body["expected_version"] = expected_version
    return client.post(
        f"/api/v1/inventory/products/{product_id}/adjustments",
        headers={**auth_headers("operations_admin"), "X-Request-ID": "inventory-adjustment"},
        json=body,
    )


def test_initial_inventory_and_customer_availability(client: Any, auth_headers: Any) -> None:
    product = _product(client, auth_headers)
    created = _initialize(client, auth_headers, product["id"], quantity=12, threshold=3)

    availability = client.get(
        f"/api/v1/inventory/products/{product['id']}/availability",
        headers=auth_headers("customer"),
    )

    assert created["inventory"]["quantity_on_hand"] == 12
    assert created["inventory"]["quantity_reserved"] == 0
    assert created["inventory"]["quantity_available"] == 12
    assert created["movement"]["movement_type"] == "INITIAL_STOCK"
    assert created["movement"]["correlation_id"] == "inventory-init"
    assert availability.status_code == 200
    assert availability.json()["quantity_available"] == 12
    assert "quantity_on_hand" not in availability.json()
    assert "quantity_reserved" not in availability.json()


def test_customer_cannot_discover_inactive_product_availability(
    client: Any, auth_headers: Any
) -> None:
    product = _product(client, auth_headers)
    _initialize(client, auth_headers, product["id"])
    client.post(
        f"/api/v1/products/{product['id']}/deactivate",
        headers=auth_headers("operations_admin"),
    )

    customer = client.get(
        f"/api/v1/inventory/products/{product['id']}/availability",
        headers=auth_headers("customer"),
    )
    support = client.get(
        f"/api/v1/inventory/products/{product['id']}/availability",
        headers=auth_headers("support"),
    )

    assert customer.status_code == 404
    assert support.status_code == 200


def test_stock_increase_decrease_and_append_only_movements(client: Any, auth_headers: Any) -> None:
    product = _product(client, auth_headers)
    _initialize(client, auth_headers, product["id"])

    receipt = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="STOCK_RECEIPT",
        delta=5,
        key="receipt-stock-001",
        expected_version=1,
    )
    damage = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="DAMAGE",
        delta=-4,
        key="damage-stock-001",
        expected_version=2,
    )
    history = client.get(
        f"/api/v1/inventory/products/{product['id']}/movements",
        headers=auth_headers("support"),
    )

    assert receipt.status_code == 200
    assert receipt.json()["movement"]["previous_quantity_on_hand"] == 10
    assert receipt.json()["movement"]["resulting_quantity_on_hand"] == 15
    assert damage.status_code == 200
    assert damage.json()["inventory"]["quantity_on_hand"] == 11
    assert history.status_code == 200
    assert history.json()["total"] == 3
    assert {item["movement_type"] for item in history.json()["items"]} == {
        "INITIAL_STOCK",
        "STOCK_RECEIPT",
        "DAMAGE",
    }


def test_negative_stock_and_invalid_movement_semantics_are_rejected(
    client: Any, auth_headers: Any
) -> None:
    product = _product(client, auth_headers)
    _initialize(client, auth_headers, product["id"], quantity=2)

    negative = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="MANUAL_ADJUSTMENT",
        delta=-3,
        key="negative-stock-001",
    )
    invalid_receipt = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="STOCK_RECEIPT",
        delta=-1,
        key="invalid-receipt-001",
    )
    reserved_type = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="RESERVATION",
        delta=1,
        key="future-reservation-001",
    )

    assert negative.status_code == 400
    assert invalid_receipt.status_code == 400
    assert reserved_type.status_code == 422


def test_reserved_balance_invariant_and_availability_calculation() -> None:
    valid = InventoryItem(product_id=uuid4(), quantity_on_hand=10, quantity_reserved=4)
    invalid = InventoryItem(product_id=uuid4(), quantity_on_hand=5, quantity_reserved=6)

    validate_balances(valid)
    assert valid.quantity_available == 6
    with pytest.raises(InvalidOperationError):
        validate_balances(invalid)


def test_movement_domain_record_is_immutable() -> None:
    movement = InventoryMovement(
        inventory_item_id=uuid4(),
        product_id=uuid4(),
        movement_type=InventoryMovementType.INITIAL_STOCK,
        quantity_delta=1,
        previous_quantity_on_hand=0,
        resulting_quantity_on_hand=1,
        previous_quantity_reserved=0,
        resulting_quantity_reserved=0,
        actor_subject="operations-user",
        correlation_id="immutable-test",
        idempotency_key="immutable-movement-001",
        reason="Initial count",
    )

    with pytest.raises(FrozenInstanceError):
        movement.quantity_delta = 2  # type: ignore[misc]


def test_idempotent_adjustment_does_not_create_duplicate_movement(
    client: Any, auth_headers: Any
) -> None:
    product = _product(client, auth_headers)
    _initialize(client, auth_headers, product["id"])
    first = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="STOCK_RECEIPT",
        delta=2,
        key="idempotent-receipt-001",
    )
    replay = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="STOCK_RECEIPT",
        delta=2,
        key="idempotent-receipt-001",
    )
    history = client.get(
        f"/api/v1/inventory/products/{product['id']}/movements",
        headers=auth_headers("support"),
    )

    assert first.status_code == replay.status_code == 200
    assert first.json()["movement"]["id"] == replay.json()["movement"]["id"]
    assert history.json()["total"] == 2


def test_stale_concurrent_updates_cannot_overwrite_each_other(
    client: Any, auth_headers: Any
) -> None:
    product = _product(client, auth_headers)
    _initialize(client, auth_headers, product["id"], quantity=10)
    service = InventoryService(client.application.state.unit_of_work_factory)
    actor = Principal(
        subject="concurrent-operations-user",
        username="operations",
        email=None,
        roles=frozenset({"operations_admin"}),
    )

    async def apply(delta: int, key: str) -> object:
        try:
            return await service.adjust(
                actor,
                UUID(product["id"]),
                InventoryMovementType.MANUAL_ADJUSTMENT,
                delta,
                "Concurrent adjustment test",
                None,
                key,
                1,
                key,
            )
        except ConflictError as exc:
            return exc

    async def run_concurrently() -> list[object]:
        return list(
            await asyncio.gather(
                apply(2, "concurrent-adjustment-001"),
                apply(3, "concurrent-adjustment-002"),
            )
        )

    results = client._loop.run_until_complete(run_concurrently())  # type: ignore[attr-defined]
    final = client.get(
        f"/api/v1/inventory/products/{product['id']}", headers=auth_headers("support")
    )

    assert sum(isinstance(result, ConflictError) for result in results) == 1
    assert final.json()["quantity_on_hand"] in {12, 13}
    assert final.json()["version"] == 2


def test_inventory_authorization_matrix(client: Any, auth_headers: Any) -> None:
    product = _product(client, auth_headers)
    _initialize(client, auth_headers, product["id"])

    customer_operational_read = client.get(
        f"/api/v1/inventory/products/{product['id']}", headers=auth_headers("customer")
    )
    customer_write = client.post(
        f"/api/v1/inventory/products/{product['id']}/adjustments",
        headers=auth_headers("customer"),
        json={
            "movement_type": "CORRECTION",
            "quantity_delta": 1,
            "reason": "Unauthorized mutation",
            "idempotency_key": "customer-write-002",
        },
    )
    support_read = client.get(
        f"/api/v1/inventory/products/{product['id']}/movements",
        headers=auth_headers("support"),
    )
    support_write = client.post(
        f"/api/v1/inventory/products/{product['id']}/adjustments",
        headers=auth_headers("support"),
        json={
            "movement_type": "CORRECTION",
            "quantity_delta": 1,
            "reason": "Unauthorized mutation",
            "idempotency_key": "support-write-001",
        },
    )

    assert customer_operational_read.status_code == 403
    assert customer_write.status_code == 403
    assert support_read.status_code == 200
    assert support_write.status_code == 403


def test_inventory_statistics_and_filtering_are_calculated(client: Any, auth_headers: Any) -> None:
    configurations = (("101", 10, 2), ("102", 2, 5), ("103", 0, 0))
    for suffix, quantity, threshold in configurations:
        product = _product(client, auth_headers, suffix)
        _initialize(
            client,
            auth_headers,
            product["id"],
            quantity=quantity,
            threshold=threshold,
            key=f"initial-stock-{suffix}",
        )

    statistics = client.get(
        "/api/v1/inventory/statistics", headers=auth_headers("operations_admin")
    )
    low_stock = client.get(
        "/api/v1/inventory?state=low_stock&limit=1", headers=auth_headers("support")
    )

    assert statistics.status_code == 200
    assert statistics.json()["total_products_tracked"] == 3
    assert statistics.json()["in_stock_products"] == 1
    assert statistics.json()["low_stock_products"] == 1
    assert statistics.json()["out_of_stock_products"] == 1
    assert statistics.json()["total_units_on_hand"] == 12
    assert statistics.json()["reserved_units"] == 0
    assert statistics.json()["available_units"] == 12
    assert low_stock.status_code == 200
    assert low_stock.json()["total"] == 1


def test_inventory_input_and_version_validation(client: Any, auth_headers: Any) -> None:
    product = _product(client, auth_headers)
    _initialize(client, auth_headers, product["id"])

    stale = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="CORRECTION",
        delta=1,
        key="stale-version-001",
        expected_version=99,
    )
    zero = _adjust(
        client,
        auth_headers,
        product["id"],
        movement_type="CORRECTION",
        delta=0,
        key="zero-adjustment-001",
    )
    invalid_page = client.get("/api/v1/inventory?limit=0", headers=auth_headers("support"))
    settings = client.patch(
        f"/api/v1/inventory/products/{product['id']}/settings",
        headers=auth_headers("operations_admin"),
        json={"reorder_threshold": 7, "expected_version": 1},
    )
    stale_settings = client.patch(
        f"/api/v1/inventory/products/{product['id']}/settings",
        headers=auth_headers("operations_admin"),
        json={"reorder_threshold": 8, "expected_version": 1},
    )

    assert stale.status_code == 409
    assert zero.status_code == 400
    assert invalid_page.status_code == 422
    assert settings.status_code == 200
    assert settings.json()["reorder_threshold"] == 7
    assert settings.json()["version"] == 2
    assert stale_settings.status_code == 409
