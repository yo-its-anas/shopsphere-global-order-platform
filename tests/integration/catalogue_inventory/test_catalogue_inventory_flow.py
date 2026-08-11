"""Live product, pricing, inventory, RBAC, and gateway integration coverage."""

from __future__ import annotations

import secrets
import time
from urllib.parse import quote

import pytest

from customer_identity.http import assert_status

from .conftest import CatalogueContext

pytestmark = pytest.mark.catalogue_inventory_integration


def test_configured_api_layer_is_reachable(catalogue_context: CatalogueContext) -> None:
    context = catalogue_context
    response = context.api("customer", "GET", "products?offset=0&limit=1")
    assert_status(response, 200)
    if context.config.gateway_url is None:
        pytest.skip(
            "API Gateway URL was not configured; service integration is available but "
            "gateway/end-to-end validation is pending."
        )
    assert context.config.api_layer == "gateway"


def test_product_category_lifecycle_search_and_rbac(
    catalogue_context: CatalogueContext,
) -> None:
    context = catalogue_context
    category = context.create_category()
    product = context.create_product(category["id"])

    duplicate = context.api(
        "operations_admin",
        "POST",
        "products",
        json_body={
            "sku": product["sku"],
            "name": "Duplicate Synthetic Product",
            "category_id": category["id"],
            "status": "active",
            "is_searchable": True,
        },
    )
    assert_status(duplicate, 409)

    retrieved = context.api("customer", "GET", f"products/{product['id']}")
    assert_status(retrieved, 200)
    assert retrieved.json()["sku"] == product["sku"]

    updated_name = f"Updated Synthetic Product {secrets.token_hex(4)}"
    updated = context.api(
        "operations_admin",
        "PATCH",
        f"products/{product['id']}",
        json_body={"name": updated_name},
    )
    assert_status(updated, 200)
    assert updated.json()["name"] == updated_name

    search = context.api(
        "customer", "GET", f"products?query={quote(updated_name)}&offset=0&limit=10"
    )
    assert_status(search, 200)
    assert any(item["id"] == product["id"] for item in search.json()["items"])

    filtered = context.api(
        "customer",
        "GET",
        f"products?category_id={category['id']}&status=active&offset=0&limit=1",
    )
    assert_status(filtered, 200)
    assert filtered.json()["offset"] == 0
    assert filtered.json()["limit"] == 1
    assert all(
        item["category_id"] == category["id"] for item in filtered.json()["items"]
    )

    page = context.api("customer", "GET", "products?offset=1&limit=1&sort_by=sku")
    assert_status(page, 200)
    assert page.json()["offset"] == 1
    assert page.json()["limit"] == 1

    denied_product = context.api(
        "customer",
        "PATCH",
        f"products/{product['id']}",
        json_body={"name": "Unauthorized Product Change"},
    )
    assert_status(denied_product, 403)
    denied_category = context.api(
        "customer",
        "POST",
        "categories",
        json_body={"name": "Unauthorized Category", "slug": "unauthorized-category"},
    )
    assert_status(denied_category, 403)


def test_pricing_validation_update_and_customer_read(
    catalogue_context: CatalogueContext,
) -> None:
    context = catalogue_context
    product = context.create_product(context.create_category()["id"])

    created = context.api(
        "operations_admin",
        "PUT",
        f"products/{product['id']}/prices/USD",
        json_body={"amount": "19.9900"},
    )
    assert_status(created, 200)
    assert created.json()["amount"] == "19.9900"

    updated = context.api(
        "operations_admin",
        "PUT",
        f"products/{product['id']}/prices/USD",
        json_body={"amount": "21.5000"},
    )
    assert_status(updated, 200)
    assert updated.json()["amount"] == "21.5000"

    prices = context.api("customer", "GET", f"products/{product['id']}/prices")
    assert_status(prices, 200)
    assert prices.json()["items"][0]["currency_code"] == "USD"
    assert prices.json()["items"][0]["amount"] == "21.5000"

    invalid_amount = context.api(
        "operations_admin",
        "PUT",
        f"products/{product['id']}/prices/USD",
        json_body={"amount": "-1.00"},
    )
    assert_status(invalid_amount, 422)
    invalid_currency = context.api(
        "operations_admin",
        "PUT",
        f"products/{product['id']}/prices/ZZZ",
        json_body={"amount": "10.00"},
    )
    assert_status(invalid_currency, 400)


def test_inventory_adjustments_availability_movements_and_statistics(
    catalogue_context: CatalogueContext,
) -> None:
    context = catalogue_context
    product = context.create_product(context.create_category()["id"])
    prefix = f"inventory-it-{secrets.token_hex(6)}"

    initialized = context.api(
        "operations_admin",
        "POST",
        f"inventory/products/{product['id']}/initialize",
        json_body={
            "quantity_on_hand": 5,
            "reorder_threshold": 3,
            "reason": "Synthetic integration stock initialization",
            "reference": "integration-test",
            "idempotency_key": f"{prefix}-initial",
        },
        request_id=f"{prefix}-initial",
    )
    assert_status(initialized, 201)
    assert initialized.json()["inventory"]["quantity_available"] == 5

    increased = context.api(
        "operations_admin",
        "POST",
        f"inventory/products/{product['id']}/adjustments",
        json_body={
            "movement_type": "STOCK_RECEIPT",
            "quantity_delta": 2,
            "reason": "Synthetic integration stock receipt",
            "idempotency_key": f"{prefix}-increase",
            "expected_version": initialized.json()["inventory"]["version"],
        },
    )
    assert_status(increased, 200)
    assert increased.json()["inventory"]["quantity_on_hand"] == 7

    low = context.api(
        "operations_admin",
        "POST",
        f"inventory/products/{product['id']}/adjustments",
        json_body={
            "movement_type": "DAMAGE",
            "quantity_delta": -4,
            "reason": "Synthetic integration low-stock transition",
            "idempotency_key": f"{prefix}-low",
            "expected_version": increased.json()["inventory"]["version"],
        },
    )
    assert_status(low, 200)
    assert low.json()["inventory"]["quantity_available"] == 3
    assert low.json()["inventory"]["state"] == "low_stock"

    rejected = context.api(
        "operations_admin",
        "POST",
        f"inventory/products/{product['id']}/adjustments",
        json_body={
            "movement_type": "DAMAGE",
            "quantity_delta": -4,
            "reason": "Synthetic negative-stock attempt",
            "idempotency_key": f"{prefix}-negative",
        },
    )
    assert_status(rejected, 400)

    emptied = context.api(
        "operations_admin",
        "POST",
        f"inventory/products/{product['id']}/adjustments",
        json_body={
            "movement_type": "DAMAGE",
            "quantity_delta": -3,
            "reason": "Synthetic integration out-of-stock transition",
            "idempotency_key": f"{prefix}-empty",
            "expected_version": low.json()["inventory"]["version"],
        },
    )
    assert_status(emptied, 200)
    assert emptied.json()["inventory"]["state"] == "out_of_stock"
    assert emptied.json()["inventory"]["quantity_available"] == 0

    availability = context.api(
        "customer", "GET", f"inventory/products/{product['id']}/availability"
    )
    assert_status(availability, 200)
    assert availability.json()["quantity_available"] == 0

    customer_inventory = context.api(
        "customer", "GET", f"inventory/products/{product['id']}"
    )
    assert_status(customer_inventory, 403)
    customer_adjustment = context.api(
        "customer",
        "POST",
        f"inventory/products/{product['id']}/adjustments",
        json_body={
            "movement_type": "STOCK_RECEIPT",
            "quantity_delta": 1,
            "reason": "Unauthorized stock mutation",
            "idempotency_key": f"{prefix}-denied",
        },
    )
    assert_status(customer_adjustment, 403)

    movements = context.api(
        "support",
        "GET",
        f"inventory/products/{product['id']}/movements?offset=0&limit=20",
    )
    assert_status(movements, 200)
    assert movements.json()["total"] == 4
    assert {item["movement_type"] for item in movements.json()["items"]} == {
        "INITIAL_STOCK",
        "STOCK_RECEIPT",
        "DAMAGE",
    }
    assert all(item["actor_subject"] for item in movements.json()["items"])
    assert all(item["correlation_id"] for item in movements.json()["items"])

    statistics = context.api("support", "GET", "inventory/statistics")
    assert_status(statistics, 200)
    values = statistics.json()
    assert values["total_products_tracked"] >= 1
    assert values["out_of_stock_products"] >= 1
    assert values["total_units_on_hand"] >= values["available_units"]
    assert values["reserved_units"] >= 0


def test_missing_invalid_and_insufficient_role_tokens(
    catalogue_context: CatalogueContext,
) -> None:
    context = catalogue_context
    missing = context.http.request("GET", context.config.api("products"))
    assert_status(missing, 401)
    invalid = context.http.request(
        "GET",
        context.config.api("products"),
        token=f"not-a-valid-jwt-{secrets.token_hex(8)}",
    )
    assert_status(invalid, 401)

    denied = context.api(
        "support",
        "POST",
        "categories",
        json_body={
            "name": "Denied Support Category",
            "slug": "denied-support-category",
        },
    )
    assert_status(denied, 403)


def test_expired_token_is_rejected(catalogue_context: CatalogueContext) -> None:
    context = catalogue_context
    expiring = context.keycloak.acquire_user_token(context.identities["customer"])
    wait_seconds = expiring.expires_in + context.config.jwt_clock_skew_seconds + 1
    if wait_seconds > context.config.maximum_expiry_wait_seconds:
        pytest.skip(
            "The dedicated test client's token lifetime exceeds the bounded expiration wait."
        )
    time.sleep(wait_seconds)
    expired = context.http.request(
        "GET", context.config.api("products"), token=expiring.value
    )
    assert_status(expired, 401)


def test_cache_invalidation_returns_authoritative_product_state(
    catalogue_context: CatalogueContext,
) -> None:
    context = catalogue_context
    product = context.create_product(context.create_category()["id"])
    first = context.api("customer", "GET", f"products/{product['id']}")
    assert_status(first, 200)

    new_name = f"Cache Invalidation Result {secrets.token_hex(4)}"
    changed = context.api(
        "operations_admin",
        "PATCH",
        f"products/{product['id']}",
        json_body={"name": new_name},
    )
    assert_status(changed, 200)
    after_change = context.api("customer", "GET", f"products/{product['id']}")
    assert_status(after_change, 200)
    assert after_change.json()["name"] == new_name
