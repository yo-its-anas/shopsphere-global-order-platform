"""Isolated database, signed-token, and catalogue fixtures."""

import asyncio
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import TracebackType
from typing import Any
from uuid import UUID

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError, ProductUnavailableError
from app.core.security import KeycloakTokenVerifier
from app.domain.models import CartItem, CatalogueProductSnapshot, ShoppingCart
from app.main import create_app

TEST_ISSUER = "https://identity.test/realms/shopsphere"


class ApiClient:
    """Synchronous facade over the repository's in-process ASGI transport."""

    def __init__(self, application: object) -> None:
        self._application = application

    def request(self, method: str, url: str, **kwargs: Any) -> httpx2.Response:
        async def send() -> httpx2.Response:
            transport = httpx2.ASGITransport(app=self._application)
            async with httpx2.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as async_client:
                return await async_client.request(method, url, **kwargs)

        return asyncio.run(send())

    def get(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("DELETE", url, **kwargs)


class StubCatalogueClient:
    def __init__(self) -> None:
        self.products: dict[UUID, CatalogueProductSnapshot] = {}
        self.unavailable = False
        self.tokens: list[str] = []
        self.correlation_ids: list[str] = []

    def add_product(
        self,
        product_id: UUID,
        *,
        price: str = "12.5000",
        active: bool = True,
        quantity_available: int | None = 20,
    ) -> None:
        self.products[product_id] = CatalogueProductSnapshot(
            product_id=product_id,
            sku=f"SKU-{str(product_id)[:8]}",
            name="Simulated Product",
            status="active" if active else "inactive",
            is_searchable=active,
            unit_price=Decimal(price),
            currency_code="USD",
            quantity_available=quantity_available,
        )

    async def get_product_snapshot(
        self,
        product_id: UUID,
        currency_code: str,
        access_token: str,
        correlation_id: str,
    ) -> CatalogueProductSnapshot:
        self.tokens.append(access_token)
        self.correlation_ids.append(correlation_id)
        if self.unavailable:
            raise DependencyUnavailableError
        product = self.products.get(product_id)
        if product is None or product.status != "active" or not product.is_searchable:
            raise ProductUnavailableError
        if product.currency_code != currency_code:
            raise ProductUnavailableError
        return product


@pytest.fixture
def settings() -> Settings:
    return Settings(
        service_name="order-service",
        service_version="0.1.0",
        environment="test",
        log_level="WARNING",
        keycloak_issuer=TEST_ISSUER,
        catalogue_service_url="http://catalogue.test/api/v1",
        cart_max_item_quantity=10,
    )


class MemoryCartRepository:
    """Persistence-independent test adapter for the cart repository contract."""

    def __init__(self, store: dict[str, dict[UUID, object]]) -> None:
        self._carts = store["carts"]
        self._items = store["items"]

    async def get_active_cart(
        self, customer_subject: str, currency_code: str, *, for_update: bool = False
    ) -> ShoppingCart | None:
        del for_update
        return next(
            (
                cart
                for cart in self._carts.values()
                if isinstance(cart, ShoppingCart)
                and cart.customer_identity_subject == customer_subject
                and cart.currency_code == currency_code
            ),
            None,
        )

    async def get_cart_by_id(
        self, cart_id: UUID, *, for_update: bool = False
    ) -> ShoppingCart | None:
        del for_update
        cart = self._carts.get(cart_id)
        return cart if isinstance(cart, ShoppingCart) else None

    def add_cart(self, cart: ShoppingCart) -> None:
        self._carts[cart.id] = cart

    async def update_cart(self, cart: ShoppingCart, expected_version: int) -> bool:
        current = self._carts.get(cart.id)
        if not isinstance(current, ShoppingCart) or current.version != expected_version:
            return False
        self._carts[cart.id] = cart
        return True

    async def list_items(self, cart_id: UUID) -> list[CartItem]:
        return [
            item
            for item in self._items.values()
            if isinstance(item, CartItem) and item.cart_id == cart_id
        ]

    async def get_item_by_product(
        self, cart_id: UUID, product_id: UUID, *, for_update: bool = False
    ) -> CartItem | None:
        del for_update
        return next(
            (
                item
                for item in self._items.values()
                if isinstance(item, CartItem)
                and item.cart_id == cart_id
                and item.product_id == product_id
            ),
            None,
        )

    async def get_item(
        self, cart_id: UUID, item_id: UUID, *, for_update: bool = False
    ) -> CartItem | None:
        del for_update
        item = self._items.get(item_id)
        return item if isinstance(item, CartItem) and item.cart_id == cart_id else None

    def add_item(self, item: CartItem) -> None:
        self._items[item.id] = item

    async def update_item(self, item: CartItem) -> None:
        self._items[item.id] = item

    async def delete_item(self, item: CartItem) -> None:
        self._items.pop(item.id, None)

    async def clear_items(self, cart_id: UUID) -> None:
        item_ids = [
            item.id
            for item in self._items.values()
            if isinstance(item, CartItem) and item.cart_id == cart_id
        ]
        for item_id in item_ids:
            self._items.pop(item_id)


class MemoryUnitOfWork:
    def __init__(self, store: dict[str, dict[UUID, object]]) -> None:
        self.carts = MemoryCartRepository(store)

    async def __aenter__(self) -> "MemoryUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def token_factory(private_key: rsa.RSAPrivateKey) -> Any:
    def issue(
        *,
        subject: str = "customer-a",
        roles: tuple[str, ...] = ("customer",),
        expires_in: timedelta = timedelta(minutes=5),
    ) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": subject,
                "iss": TEST_ISSUER,
                "aud": "shopsphere-api",
                "iat": now,
                "exp": now + expires_in,
                "preferred_username": f"{subject}@example.test",
                "realm_access": {"roles": list(roles)},
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    return issue


@pytest.fixture
def catalogue_client() -> StubCatalogueClient:
    return StubCatalogueClient()


@pytest.fixture
def client(
    settings: Settings,
    private_key: rsa.RSAPrivateKey,
    catalogue_client: StubCatalogueClient,
) -> Iterator[ApiClient]:
    verifier = KeycloakTokenVerifier(settings)
    verifier._keys = {"test-key": private_key.public_key()}
    verifier._keys_loaded_at = float("inf")
    store: dict[str, dict[UUID, object]] = {"carts": {}, "items": {}}

    async def ready(_: object) -> bool:
        return True

    yield ApiClient(
        create_app(
            settings,
            token_verifier=verifier,
            catalogue_client=catalogue_client,
            unit_of_work_factory=lambda: MemoryUnitOfWork(store),
            readiness_check=ready,
        )
    )


@pytest.fixture
def auth_headers(token_factory: Any) -> Any:
    def build(subject: str = "customer-a", role: str = "customer") -> dict[str, str]:
        return {"Authorization": f"Bearer {token_factory(subject=subject, roles=(role,))}"}

    return build
