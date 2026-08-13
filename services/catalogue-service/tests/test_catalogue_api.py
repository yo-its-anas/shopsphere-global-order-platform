"""Product Catalogue API, persistence, search, pricing, and RBAC tests."""

from decimal import Decimal
from typing import Any
from uuid import uuid4


def _create_category(
    client: Any,
    auth_headers: Any,
    *,
    name: str = "Electronics",
    slug: str = "electronics",
    is_active: bool = True,
    parent_id: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/categories",
        headers=auth_headers("operations_admin"),
        json={
            "name": name,
            "slug": slug,
            "is_active": is_active,
            "parent_id": parent_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_product(
    client: Any,
    auth_headers: Any,
    category_id: str,
    *,
    sku: str = "SS-LAPTOP-001",
    name: str = "Enterprise Laptop",
    status: str = "active",
    is_searchable: bool = True,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/products",
        headers=auth_headers("operations_admin"),
        json={
            "sku": sku,
            "name": name,
            "description": "Simulated catalogue product",
            "category_id": category_id,
            "status": status,
            "is_searchable": is_searchable,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_creates_and_updates_category(client: Any, auth_headers: Any) -> None:
    category = _create_category(client, auth_headers, slug="  ELECTRONICS  ")
    assert category["slug"] == "electronics"

    response = client.patch(
        f"/api/v1/categories/{category['id']}",
        headers=auth_headers("operations_admin"),
        json={"name": "Enterprise Electronics", "description": "Managed devices"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Enterprise Electronics"


def test_duplicate_category_slug_is_rejected(client: Any, auth_headers: Any) -> None:
    _create_category(client, auth_headers)
    response = client.post(
        "/api/v1/categories",
        headers=auth_headers("operations_admin"),
        json={"name": "Different name", "slug": "ELECTRONICS"},
    )
    assert response.status_code == 409


def test_category_parent_cycle_and_invalid_parent_are_rejected(
    client: Any, auth_headers: Any
) -> None:
    parent = _create_category(client, auth_headers, name="Parent", slug="parent")
    child = _create_category(
        client, auth_headers, name="Child", slug="child", parent_id=parent["id"]
    )

    cycle = client.patch(
        f"/api/v1/categories/{parent['id']}",
        headers=auth_headers("operations_admin"),
        json={"parent_id": child["id"]},
    )
    missing = client.post(
        "/api/v1/categories",
        headers=auth_headers("operations_admin"),
        json={"name": "Invalid", "slug": "invalid", "parent_id": str(uuid4())},
    )

    assert cycle.status_code == 400
    assert missing.status_code == 404


def test_admin_registers_product_and_duplicate_sku_is_rejected(
    client: Any, auth_headers: Any
) -> None:
    category = _create_category(client, auth_headers)
    product = _create_product(client, auth_headers, category["id"], sku="ss-laptop-001")
    assert product["sku"] == "SS-LAPTOP-001"

    duplicate = client.post(
        "/api/v1/products",
        headers=auth_headers("operations_admin"),
        json={
            "sku": "SS-LAPTOP-001",
            "name": "Duplicate",
            "category_id": category["id"],
        },
    )
    assert duplicate.status_code == 409


def test_admin_updates_product_without_mass_assigning_sku(client: Any, auth_headers: Any) -> None:
    category = _create_category(client, auth_headers)
    product = _create_product(client, auth_headers, category["id"])

    updated = client.patch(
        f"/api/v1/products/{product['id']}",
        headers=auth_headers("operations_admin"),
        json={"name": "Updated Laptop"},
    )
    mass_assignment = client.patch(
        f"/api/v1/products/{product['id']}",
        headers=auth_headers("operations_admin"),
        json={"sku": "REASSIGNED"},
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Laptop"
    assert updated.json()["sku"] == "SS-LAPTOP-001"
    assert mass_assignment.status_code == 422


def test_deactivated_product_is_hidden_from_customer_but_visible_to_support(
    client: Any, auth_headers: Any
) -> None:
    category = _create_category(client, auth_headers)
    product = _create_product(client, auth_headers, category["id"])

    deactivated = client.post(
        f"/api/v1/products/{product['id']}/deactivate",
        headers=auth_headers("operations_admin"),
    )
    customer_read = client.get(
        f"/api/v1/products/{product['id']}", headers=auth_headers("customer")
    )
    support_read = client.get(f"/api/v1/products/{product['id']}", headers=auth_headers("support"))

    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    assert deactivated.json()["is_searchable"] is False
    assert customer_read.status_code == 404
    assert support_read.status_code == 200


def test_price_update_uses_decimal_and_retains_history(client: Any, auth_headers: Any) -> None:
    category = _create_category(client, auth_headers)
    product = _create_product(client, auth_headers, category["id"])
    path = f"/api/v1/products/{product['id']}/prices/USD"

    first = client.put(path, headers=auth_headers("operations_admin"), json={"amount": "19.9900"})
    second = client.put(path, headers=auth_headers("operations_admin"), json={"amount": "21.5000"})
    current = client.get(
        f"/api/v1/products/{product['id']}/prices", headers=auth_headers("customer")
    )
    history = client.get(
        f"/api/v1/products/{product['id']}/prices?include_history=true",
        headers=auth_headers("support"),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert Decimal(current.json()["items"][0]["amount"]) == Decimal("21.5000")
    assert len(current.json()["items"]) == 1
    assert len(history.json()["items"]) == 2
    assert sum(item["is_active"] for item in history.json()["items"]) == 1


def test_invalid_price_and_currency_are_rejected(client: Any, auth_headers: Any) -> None:
    category = _create_category(client, auth_headers)
    product = _create_product(client, auth_headers, category["id"])
    base = f"/api/v1/products/{product['id']}/prices"

    zero = client.put(f"{base}/USD", headers=auth_headers("operations_admin"), json={"amount": "0"})
    excessive_precision = client.put(
        f"{base}/USD",
        headers=auth_headers("operations_admin"),
        json={"amount": "1.12345"},
    )
    unsupported = client.put(
        f"{base}/ZZZ", headers=auth_headers("operations_admin"), json={"amount": "10.00"}
    )

    assert zero.status_code == 422
    assert excessive_precision.status_code == 422
    assert unsupported.status_code == 400


def test_customer_and_support_cannot_modify_catalogue(client: Any, auth_headers: Any) -> None:
    customer_write = client.post(
        "/api/v1/categories",
        headers=auth_headers("customer"),
        json={"name": "Forbidden", "slug": "forbidden"},
    )
    support_write = client.post(
        "/api/v1/categories",
        headers=auth_headers("support"),
        json={"name": "Forbidden", "slug": "forbidden"},
    )

    assert customer_write.status_code == 403
    assert support_write.status_code == 403


def test_customer_and_support_read_permissions(client: Any, auth_headers: Any) -> None:
    category = _create_category(client, auth_headers)
    product = _create_product(client, auth_headers, category["id"])

    customer = client.get("/api/v1/products", headers=auth_headers("customer"))
    support = client.get(f"/api/v1/products/{product['id']}", headers=auth_headers("support"))

    assert customer.status_code == 200
    assert customer.json()["total"] == 1
    assert support.status_code == 200


def test_search_filter_sort_and_pagination(client: Any, auth_headers: Any) -> None:
    laptops = _create_category(client, auth_headers, name="Laptops", slug="laptops")
    phones = _create_category(client, auth_headers, name="Phones", slug="phones")
    _create_product(
        client,
        auth_headers,
        laptops["id"],
        sku="LAP-002",
        name="Beta Laptop",
    )
    _create_product(
        client,
        auth_headers,
        laptops["id"],
        sku="LAP-001",
        name="Alpha Laptop",
    )
    _create_product(
        client,
        auth_headers,
        phones["id"],
        sku="PHN-001",
        name="Enterprise Phone",
    )

    search = client.get(
        f"/api/v1/products?query=laptop&category_id={laptops['id']}&sort_by=sku&limit=1",
        headers=auth_headers("customer"),
    )
    second_page = client.get(
        f"/api/v1/products?query=laptop&category_id={laptops['id']}&sort_by=sku&limit=1&offset=1",
        headers=auth_headers("customer"),
    )
    exact_sku = client.get("/api/v1/products?sku=phn-001", headers=auth_headers("customer"))

    assert search.status_code == 200
    assert search.json()["total"] == 2
    assert search.json()["items"][0]["sku"] == "LAP-001"
    assert second_page.json()["items"][0]["sku"] == "LAP-002"
    assert exact_sku.json()["items"][0]["sku"] == "PHN-001"


def test_status_filter_is_honoured_for_support_but_not_customer(
    client: Any, auth_headers: Any
) -> None:
    category = _create_category(client, auth_headers)
    _create_product(
        client,
        auth_headers,
        category["id"],
        sku="DRAFT-001",
        name="Draft Product",
        status="draft",
        is_searchable=False,
    )

    customer = client.get("/api/v1/products?status=draft", headers=auth_headers("customer"))
    support = client.get("/api/v1/products?status=draft", headers=auth_headers("support"))

    assert customer.json()["total"] == 0
    assert support.json()["total"] == 1


def test_unauthorized_invalid_token_and_input_validation(client: Any, auth_headers: Any) -> None:
    unauthorized = client.get("/api/v1/products")
    invalid_token = client.get("/api/v1/products", headers={"Authorization": "Bearer not-a-jwt"})
    invalid_uuid = client.get("/api/v1/products/not-a-uuid", headers=auth_headers("customer"))
    invalid_pagination = client.get(
        "/api/v1/products?limit=0&offset=-1", headers=auth_headers("customer")
    )
    invalid_sort = client.get("/api/v1/products?sort_by=amount", headers=auth_headers("customer"))
    category = _create_category(client, auth_headers)
    product = _create_product(client, auth_headers, category["id"])
    null_required_field = client.patch(
        f"/api/v1/products/{product['id']}",
        headers=auth_headers("operations_admin"),
        json={"status": None},
    )

    assert unauthorized.status_code == 401
    assert invalid_token.status_code == 401
    assert invalid_uuid.status_code == 422
    assert invalid_pagination.status_code == 422
    assert invalid_sort.status_code == 422
    assert null_required_field.status_code == 422
