"""Signed-token and repository-isolated Product Catalogue test fixtures."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import Settings
from app.core.security import KeycloakTokenVerifier
from app.domain.models import (
    AvailabilityState,
    InventoryItem,
    InventoryMovement,
    Product,
    ProductCategory,
    ProductPrice,
    ProductStatus,
)
from app.main import create_app

TEST_ISSUER = "https://identity.test/realms/shopsphere"


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    content: bytes
    headers: dict[str, str]

    @property
    def text(self) -> str:
        return self.content.decode()

    def json(self) -> Any:
        return json.loads(self.content)


class ApiHeaders(dict[str, str]):
    def __getitem__(self, key: str) -> str:
        return super().__getitem__(key.casefold())


class ApiClient:
    """Minimal deterministic ASGI protocol client for API-boundary tests."""

    def __init__(self, application: Any) -> None:
        self._application = application
        self._loop = asyncio.new_event_loop()

    @property
    def application(self) -> Any:
        return self._application

    def close(self) -> None:
        self._loop.close()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> ApiResponse:
        parsed = urlsplit(url)
        body = json.dumps(json_body).encode() if json_body is not None else b""
        request_headers = {key.casefold(): value for key, value in (headers or {}).items()}
        if json_body is not None:
            request_headers["content-type"] = "application/json"
        encoded_headers = [
            (key.encode("latin-1"), value.encode("latin-1"))
            for key, value in request_headers.items()
        ]

        async def send_request() -> ApiResponse:
            request_sent = False
            response_complete = asyncio.Event()
            response_status = 500
            response_headers = ApiHeaders()
            response_parts: list[bytes] = []

            async def receive() -> dict[str, object]:
                nonlocal request_sent
                if not request_sent:
                    request_sent = True
                    return {"type": "http.request", "body": body, "more_body": False}
                await response_complete.wait()
                return {"type": "http.disconnect"}

            async def send(message: dict[str, Any]) -> None:
                nonlocal response_status
                if message["type"] == "http.response.start":
                    response_status = int(message["status"])
                    response_headers.update(
                        {
                            key.decode("latin-1").casefold(): value.decode("latin-1")
                            for key, value in message.get("headers", [])
                        }
                    )
                elif message["type"] == "http.response.body":
                    response_parts.append(message.get("body", b""))
                    if not message.get("more_body", False):
                        response_complete.set()

            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": parsed.path,
                "raw_path": parsed.path.encode(),
                "query_string": parsed.query.encode(),
                "root_path": "",
                "headers": encoded_headers,
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
                "state": {},
            }
            await self._application(scope, receive, send)
            return ApiResponse(response_status, b"".join(response_parts), response_headers)

        return self._loop.run_until_complete(send_request())

    def get(self, url: str, **kwargs: Any) -> ApiResponse:
        return self.request("GET", url, headers=kwargs.get("headers"))

    def post(self, url: str, **kwargs: Any) -> ApiResponse:
        return self.request(
            "POST", url, headers=kwargs.get("headers"), json_body=kwargs.get("json")
        )

    def put(self, url: str, **kwargs: Any) -> ApiResponse:
        return self.request("PUT", url, headers=kwargs.get("headers"), json_body=kwargs.get("json"))

    def patch(self, url: str, **kwargs: Any) -> ApiResponse:
        return self.request(
            "PATCH", url, headers=kwargs.get("headers"), json_body=kwargs.get("json")
        )


class InMemoryCatalogueRepository:
    """Repository-contract adapter; SQLAlchemy is validated separately."""

    def __init__(self) -> None:
        self.categories: dict[UUID, ProductCategory] = {}
        self.products: dict[UUID, Product] = {}
        self.prices: dict[UUID, ProductPrice] = {}

    def add_category(self, category: ProductCategory) -> None:
        self.categories[category.id] = category

    async def get_category(self, category_id: UUID) -> ProductCategory | None:
        return self.categories.get(category_id)

    async def get_category_by_slug(self, slug: str) -> ProductCategory | None:
        return next(
            (category for category in self.categories.values() if category.slug == slug), None
        )

    async def list_categories(
        self, *, active: bool | None, offset: int, limit: int
    ) -> tuple[list[ProductCategory], int]:
        items = [
            category
            for category in self.categories.values()
            if active is None or category.is_active is active
        ]
        items.sort(key=lambda category: (category.name, str(category.id)))
        return items[offset : offset + limit], len(items)

    async def update_category(self, category: ProductCategory) -> None:
        self.categories[category.id] = category

    def add_product(self, product: Product) -> None:
        self.products[product.id] = product

    async def get_product(self, product_id: UUID) -> Product | None:
        return self.products.get(product_id)

    async def get_product_by_sku(self, sku: str) -> Product | None:
        return next((product for product in self.products.values() if product.sku == sku), None)

    async def list_products(
        self,
        *,
        query: str | None,
        sku: str | None,
        category_id: UUID | None,
        status: ProductStatus | None,
        searchable: bool | None,
        require_active_category: bool,
        offset: int,
        limit: int,
        sort_by: str,
        sort_direction: str,
    ) -> tuple[list[Product], int]:
        items = list(self.products.values())
        if query:
            needle = query.casefold()
            items = [
                product
                for product in items
                if needle
                in " ".join((product.name, product.sku, product.description or "")).casefold()
            ]
        if sku:
            items = [product for product in items if product.sku == sku]
        if category_id:
            items = [product for product in items if product.category_id == category_id]
        if status:
            items = [product for product in items if product.status is status]
        if searchable is not None:
            items = [product for product in items if product.is_searchable is searchable]
        if require_active_category:
            items = [
                product
                for product in items
                if self.categories.get(product.category_id)
                and self.categories[product.category_id].is_active
            ]
        items.sort(
            key=lambda product: (getattr(product, sort_by), str(product.id)),
            reverse=sort_direction == "desc",
        )
        return items[offset : offset + limit], len(items)

    async def update_product(self, product: Product) -> None:
        self.products[product.id] = product

    def add_price(self, price: ProductPrice) -> None:
        self.prices[price.id] = price

    async def list_prices(self, product_id: UUID, *, active_only: bool) -> list[ProductPrice]:
        items = [
            price
            for price in self.prices.values()
            if price.product_id == product_id and (not active_only or price.is_active)
        ]
        items.sort(
            key=lambda price: (price.currency_code, price.effective_from, str(price.id)),
            reverse=True,
        )
        return items

    async def close_active_price(
        self, product_id: UUID, currency_code: str, effective_to: datetime
    ) -> None:
        for price in self.prices.values():
            if (
                price.product_id == product_id
                and price.currency_code == currency_code
                and price.is_active
            ):
                price.is_active = False
                price.effective_to = effective_to
                price.updated_at = effective_to


class InMemoryInventoryStore:
    def __init__(self) -> None:
        self.items: dict[UUID, InventoryItem] = {}
        self.movements: dict[UUID, InventoryMovement] = {}
        self.locks: dict[tuple[UUID, str], asyncio.Lock] = {}


class InMemoryInventoryRepository:
    def __init__(self, store: InMemoryInventoryStore) -> None:
        self._store = store
        self._held_locks: list[asyncio.Lock] = []

    async def release_locks(self) -> None:
        for lock in reversed(self._held_locks):
            lock.release()
        self._held_locks.clear()

    def add_item(self, item: InventoryItem) -> None:
        self._store.items[item.id] = item

    async def get_item(
        self, product_id: UUID, location_code: str, *, for_update: bool = False
    ) -> InventoryItem | None:
        if for_update:
            lock = self._store.locks.setdefault((product_id, location_code), asyncio.Lock())
            await lock.acquire()
            self._held_locks.append(lock)
        return next(
            (
                item
                for item in self._store.items.values()
                if item.product_id == product_id and item.location_code == location_code
            ),
            None,
        )

    async def update_item(self, item: InventoryItem, expected_version: int) -> bool:
        current = self._store.items.get(item.id)
        if current is None or current.version != expected_version:
            return False
        self._store.items[item.id] = item
        return True

    async def list_items(
        self,
        *,
        state: AvailabilityState | None,
        location_code: str,
        offset: int,
        limit: int,
    ) -> tuple[list[InventoryItem], int]:
        items = [
            item
            for item in self._store.items.values()
            if item.location_code == location_code
            and (state is None or item.availability_state is state)
        ]
        items.sort(key=lambda item: (item.updated_at, str(item.id)), reverse=True)
        return items[offset : offset + limit], len(items)

    def add_movement(self, movement: InventoryMovement) -> None:
        self._store.movements[movement.id] = movement

    async def get_movement_by_idempotency_key(
        self, idempotency_key: str
    ) -> InventoryMovement | None:
        return next(
            (
                movement
                for movement in self._store.movements.values()
                if movement.idempotency_key == idempotency_key
            ),
            None,
        )

    async def list_movements(
        self, inventory_item_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[InventoryMovement], int]:
        movements = [
            movement
            for movement in self._store.movements.values()
            if movement.inventory_item_id == inventory_item_id
        ]
        movements.sort(key=lambda movement: (movement.occurred_at, str(movement.id)), reverse=True)
        return movements[offset : offset + limit], len(movements)

    async def statistics(self, location_code: str) -> dict[str, int]:
        items = [item for item in self._store.items.values() if item.location_code == location_code]
        return {
            "total_products_tracked": len(items),
            "in_stock_products": sum(
                item.availability_state is AvailabilityState.IN_STOCK for item in items
            ),
            "low_stock_products": sum(
                item.availability_state is AvailabilityState.LOW_STOCK for item in items
            ),
            "out_of_stock_products": sum(
                item.availability_state is AvailabilityState.OUT_OF_STOCK for item in items
            ),
            "total_units_on_hand": sum(item.quantity_on_hand for item in items),
            "reserved_units": sum(item.quantity_reserved for item in items),
            "available_units": sum(item.quantity_available for item in items),
        }


class InMemoryUnitOfWork:
    def __init__(
        self,
        repository: InMemoryCatalogueRepository,
        inventory_store: InMemoryInventoryStore,
    ) -> None:
        self.catalogue = repository
        self.inventory = InMemoryInventoryRepository(inventory_store)

    async def __aenter__(self) -> InMemoryUnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.inventory.release_locks()

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


@pytest.fixture
def settings() -> Settings:
    return Settings(
        service_name="catalogue-service",
        service_version="0.1.0",
        environment="test",
        log_level="WARNING",
        keycloak_issuer=TEST_ISSUER,
    )


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def token_factory(private_key: rsa.RSAPrivateKey) -> Any:
    def issue(
        *,
        subject: str = "catalogue-user",
        roles: tuple[str, ...] = ("customer",),
        expires_in: timedelta = timedelta(minutes=5),
        audience: str = "shopsphere-api",
        signing_key: rsa.RSAPrivateKey | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": subject,
                "iss": TEST_ISSUER,
                "aud": audience,
                "iat": now,
                "exp": now + expires_in,
                "preferred_username": subject,
                "realm_access": {"roles": list(roles)},
            },
            signing_key or private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    return issue


@pytest.fixture
def client(settings: Settings, private_key: rsa.RSAPrivateKey) -> Iterator[ApiClient]:
    verifier = KeycloakTokenVerifier(settings)
    verifier._keys = {"test-key": private_key.public_key()}
    verifier._keys_loaded_at = float("inf")
    repository = InMemoryCatalogueRepository()
    inventory_store = InMemoryInventoryStore()

    async def ready(_: object) -> bool:
        return True

    test_client = ApiClient(
        create_app(
            settings,
            token_verifier=verifier,
            unit_of_work_factory=lambda: InMemoryUnitOfWork(repository, inventory_store),
            database_readiness_checker=ready,
        )
    )
    yield test_client
    test_client.close()


@pytest.fixture
def auth_headers(token_factory: Any) -> Any:
    def build(role: str = "customer", subject: str | None = None) -> dict[str, str]:
        token = token_factory(subject=subject or f"{role}-user", roles=(role,))
        return {"Authorization": f"Bearer {token}"}

    return build
