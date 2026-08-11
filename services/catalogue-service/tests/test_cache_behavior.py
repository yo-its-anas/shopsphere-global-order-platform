"""Cache-aside hit, miss, expiry, invalidation, and graceful-degradation tests."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any
from uuid import UUID

from redis.exceptions import RedisError

from app.infrastructure.cache import RedisJsonCache


class RedisClientStub:
    def __init__(self, value: str | None = None, *, unavailable: bool = False) -> None:
        self.value = value
        self.unavailable = unavailable
        self.deleted: list[str] = []
        self.expiry: int | None = None

    async def get(self, key: str) -> str | None:
        if self.unavailable:
            raise RedisError
        return self.value

    async def set(self, key: str, value: str, *, ex: int) -> None:
        if self.unavailable:
            raise RedisError
        self.value = value
        self.expiry = ex

    async def unlink(self, *keys: str) -> None:
        if self.unavailable:
            raise RedisError
        self.deleted.extend(keys)


def _redis_adapter(client: RedisClientStub) -> RedisJsonCache:
    adapter = RedisJsonCache.__new__(RedisJsonCache)
    adapter._client = client  # type: ignore[assignment]
    return adapter


def _create_product(client: Any, auth_headers: Any, suffix: str = "CACHE-001") -> dict[str, Any]:
    category = client.post(
        "/api/v1/categories",
        headers=auth_headers("operations_admin"),
        json={"name": f"Category {suffix}", "slug": suffix.lower()},
    )
    assert category.status_code == 201, category.text
    product = client.post(
        "/api/v1/products",
        headers=auth_headers("operations_admin"),
        json={
            "sku": suffix,
            "name": "Cached Product",
            "category_id": category.json()["id"],
            "status": "active",
            "is_searchable": True,
        },
    )
    assert product.status_code == 201, product.text
    return product.json()


def _initialize_inventory(client: Any, auth_headers: Any, product_id: str) -> None:
    response = client.post(
        f"/api/v1/inventory/products/{product_id}/initialize",
        headers=auth_headers("operations_admin"),
        json={
            "quantity_on_hand": 10,
            "reorder_threshold": 2,
            "reason": "Cache test initial stock",
            "idempotency_key": "cache-initial-stock-001",
        },
    )
    assert response.status_code == 201, response.text


def test_product_cache_miss_then_hit(client: Any, auth_headers: Any) -> None:
    product = _create_product(client, auth_headers)
    cache = client.application.state.test_cache
    repository = client.application.state.test_catalogue_repository
    path = f"/api/v1/products/{product['id']}"

    first = client.get(path, headers=auth_headers("customer"))
    repository.products[UUID(product["id"])].name = "Changed outside cache"
    second = client.get(path, headers=auth_headers("customer"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["name"] == "Cached Product"
    assert cache.misses >= 1
    assert cache.hits >= 1


def test_product_cache_ttl_expiry_returns_to_authoritative_repository(
    client: Any, auth_headers: Any
) -> None:
    product = _create_product(client, auth_headers)
    cache = client.application.state.test_cache
    repository = client.application.state.test_catalogue_repository
    path = f"/api/v1/products/{product['id']}"
    client.get(path, headers=auth_headers("customer"))

    repository.products[UUID(product["id"])].name = "Authoritative Product Name"
    cache.advance(client.application.state.settings.product_cache_ttl_seconds + 1)
    response = client.get(path, headers=auth_headers("customer"))

    assert response.status_code == 200
    assert response.json()["name"] == "Authoritative Product Name"


def test_product_update_invalidates_cached_detail_and_search(
    client: Any, auth_headers: Any
) -> None:
    product = _create_product(client, auth_headers)
    detail_path = f"/api/v1/products/{product['id']}"
    client.get(detail_path, headers=auth_headers("customer"))
    client.get("/api/v1/products?query=Cached", headers=auth_headers("customer"))

    updated = client.patch(
        detail_path,
        headers=auth_headers("operations_admin"),
        json={"name": "Updated Cached Product"},
    )
    detail = client.get(detail_path, headers=auth_headers("customer"))
    search = client.get("/api/v1/products?query=Updated", headers=auth_headers("customer"))

    assert updated.status_code == 200
    assert detail.json()["name"] == "Updated Cached Product"
    assert search.json()["items"][0]["name"] == "Updated Cached Product"


def test_price_update_invalidates_cached_price(client: Any, auth_headers: Any) -> None:
    product = _create_product(client, auth_headers)
    price_path = f"/api/v1/products/{product['id']}/prices/USD"
    read_path = f"/api/v1/products/{product['id']}/prices"
    client.put(
        price_path,
        headers=auth_headers("operations_admin"),
        json={"amount": "10.0000"},
    )
    client.get(read_path, headers=auth_headers("customer"))

    changed = client.put(
        price_path,
        headers=auth_headers("operations_admin"),
        json={"amount": "12.5000"},
    )
    current = client.get(read_path, headers=auth_headers("customer"))

    assert changed.status_code == 200
    assert Decimal(current.json()["items"][0]["amount"]) == Decimal("12.5000")


def test_inventory_adjustment_invalidates_availability_snapshot(
    client: Any, auth_headers: Any
) -> None:
    product = _create_product(client, auth_headers)
    _initialize_inventory(client, auth_headers, product["id"])
    availability_path = f"/api/v1/inventory/products/{product['id']}/availability"
    initial = client.get(availability_path, headers=auth_headers("customer"))

    adjusted = client.post(
        f"/api/v1/inventory/products/{product['id']}/adjustments",
        headers=auth_headers("operations_admin"),
        json={
            "movement_type": "DAMAGE",
            "quantity_delta": -3,
            "reason": "Cache invalidation test",
            "idempotency_key": "cache-damage-stock-001",
            "expected_version": 1,
        },
    )
    current = client.get(availability_path, headers=auth_headers("customer"))

    assert initial.json()["quantity_available"] == 10
    assert adjusted.status_code == 200
    assert current.json()["quantity_available"] == 7


def test_redis_unavailable_falls_back_without_affecting_readiness(
    client: Any, auth_headers: Any
) -> None:
    product = _create_product(client, auth_headers)
    client.application.state.test_cache.unavailable = True

    detail = client.get(f"/api/v1/products/{product['id']}", headers=auth_headers("customer"))
    search = client.get("/api/v1/products?query=Cached", headers=auth_headers("customer"))
    readiness = client.get("/health/ready")

    assert detail.status_code == 200
    assert search.status_code == 200
    assert readiness.status_code == 200


def test_malformed_cached_model_is_evicted_and_reloaded(client: Any, auth_headers: Any) -> None:
    product = _create_product(client, auth_headers)
    cache = client.application.state.test_cache
    key = client.application.state.cache_keys.product(UUID(product["id"]), "customer")
    cache.entries[key] = (999.0, {"unexpected": "payload"})

    response = client.get(f"/api/v1/products/{product['id']}", headers=auth_headers("customer"))

    assert response.status_code == 200
    assert response.json()["id"] == product["id"]
    assert cache.entries[key][1]["name"] == "Cached Product"


def test_redis_adapter_ttl_malformed_json_and_outage_are_safe() -> None:
    healthy_client = RedisClientStub()
    adapter = _redis_adapter(healthy_client)
    asyncio.run(adapter.set_json("safe-key", {"value": 1}, 17, "product"))
    assert healthy_client.expiry == 17

    healthy_client.value = "{malformed"
    assert asyncio.run(adapter.get_json("safe-key", "product")) is None
    assert healthy_client.deleted == ["safe-key"]

    unavailable_adapter = _redis_adapter(RedisClientStub(unavailable=True))
    assert asyncio.run(unavailable_adapter.get_json("safe-key", "product")) is None
    asyncio.run(unavailable_adapter.set_json("safe-key", {"value": 1}, 17, "product"))
    asyncio.run(unavailable_adapter.delete("safe-key", family="product"))
