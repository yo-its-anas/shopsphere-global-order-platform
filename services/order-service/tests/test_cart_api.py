"""Shopping-cart API behavior and ownership tests."""

from typing import Any
from uuid import uuid4

from tests.conftest import ApiClient, StubCatalogueClient


def _add(
    client: ApiClient,
    headers: dict[str, str],
    catalogue: StubCatalogueClient,
    *,
    quantity: int = 1,
    price: str = "12.5000",
) -> tuple[str, dict[str, Any]]:
    product_id = uuid4()
    catalogue.add_product(product_id, price=price)
    response = client.post(
        "/api/v1/carts/me/items",
        headers=headers,
        json={"product_id": str(product_id), "quantity": quantity},
    )
    assert response.status_code == 201
    return str(product_id), response.json()


def test_empty_cart_is_created_idempotently(client: ApiClient, auth_headers: Any) -> None:
    first = client.get("/api/v1/carts/me", headers=auth_headers())
    second = client.get("/api/v1/carts/me", headers=auth_headers())

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["items"] == []
    assert first.json()["display_subtotal"] == "0.0000"
    assert first.json()["pricing_authoritative"] is False


def test_add_item_uses_catalogue_snapshot(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    product_id, cart = _add(client, auth_headers(), catalogue_client, quantity=2)

    assert cart["item_count"] == 2
    assert cart["items"][0]["product_id"] == product_id
    assert cart["items"][0]["display_quantity_available"] == 20
    assert catalogue_client.tokens and catalogue_client.correlation_ids


def test_add_existing_item_increments_one_line(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    product_id, _ = _add(client, auth_headers(), catalogue_client, quantity=2)
    response = client.post(
        "/api/v1/carts/me/items",
        headers=auth_headers(),
        json={"product_id": product_id, "quantity": 3},
    )

    assert response.status_code == 201
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["quantity"] == 5


def test_update_quantity(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    _, cart = _add(client, auth_headers(), catalogue_client)
    item_id = cart["items"][0]["id"]

    response = client.patch(
        f"/api/v1/carts/me/items/{item_id}", headers=auth_headers(), json={"quantity": 4}
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 4


def test_remove_item(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    _, cart = _add(client, auth_headers(), catalogue_client)
    response = client.delete(
        f"/api/v1/carts/me/items/{cart['items'][0]['id']}", headers=auth_headers()
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_clear_cart(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    _add(client, auth_headers(), catalogue_client)
    _add(client, auth_headers(), catalogue_client)

    response = client.delete("/api/v1/carts/me/items", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["item_count"] == 0


def test_invalid_and_excessive_quantities_are_rejected(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    product_id = uuid4()
    catalogue_client.add_product(product_id)

    for quantity, expected_status in ((0, 422), (-1, 422), (11, 400)):
        response = client.post(
            "/api/v1/carts/me/items",
            headers=auth_headers(),
            json={"product_id": str(product_id), "quantity": quantity},
        )
        assert response.status_code == expected_status


def test_inactive_and_missing_products_are_rejected(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    inactive_id = uuid4()
    catalogue_client.add_product(inactive_id, active=False)

    for product_id in (inactive_id, uuid4()):
        response = client.post(
            "/api/v1/carts/me/items",
            headers=auth_headers(),
            json={"product_id": str(product_id), "quantity": 1},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "product_unavailable"


def test_authentication_and_customer_role_are_required(
    client: ApiClient, auth_headers: Any
) -> None:
    missing = client.get("/api/v1/carts/me")
    support = client.get("/api/v1/carts/me", headers=auth_headers(role="support"))

    assert missing.status_code == 401
    assert support.status_code == 403


def test_customer_cannot_modify_another_customers_item(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    _, cart_a = _add(client, auth_headers("customer-a"), catalogue_client)
    item_a = cart_a["items"][0]["id"]
    cart_b = client.get("/api/v1/carts/me", headers=auth_headers("customer-b"))

    response = client.patch(
        f"/api/v1/carts/me/items/{item_a}",
        headers=auth_headers("customer-b"),
        json={"quantity": 2},
    )

    assert cart_b.status_code == 200
    assert cart_b.json()["id"] != cart_a["id"]
    assert response.status_code == 404


def test_catalogue_unavailable_returns_safe_dependency_error(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    catalogue_client.unavailable = True

    response = client.post(
        "/api/v1/carts/me/items",
        headers=auth_headers(),
        json={"product_id": str(uuid4()), "quantity": 1},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dependency_unavailable"


def test_preliminary_subtotal_is_decimal_and_non_authoritative(
    client: ApiClient, auth_headers: Any, catalogue_client: StubCatalogueClient
) -> None:
    _, cart = _add(client, auth_headers(), catalogue_client, quantity=3, price="19.9900")

    assert cart["display_subtotal"] == "59.9700"
    assert cart["items"][0]["display_line_subtotal"] == "59.9700"
    assert cart["pricing_authoritative"] is False
    assert "revalidated at checkout" in cart["pricing_notice"]
