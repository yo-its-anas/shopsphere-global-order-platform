"""Isolated database and signed-token test fixtures."""

import asyncio
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings
from app.core.security import KeycloakTokenVerifier
from app.domain.models import CustomerActivity
from app.infrastructure.orm_models import Base
from app.main import create_app

TEST_ISSUER = "https://identity.test/realms/shopsphere"


class ApiClient:
    """Synchronous facade over httpx2's in-process ASGI transport."""

    def __init__(self, application: object) -> None:
        self._application = application

    @property
    def application(self) -> object:
        return self._application

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

    def put(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("DELETE", url, **kwargs)


class StubIdentityActivityProvider:
    """Deterministic source-neutral activity provider for API tests."""

    def __init__(self) -> None:
        self.events: list[CustomerActivity] = []
        self.requested_subjects: list[str] = []

    async def list_activity(
        self, identity_provider_subject: str, offset: int, limit: int
    ) -> list[CustomerActivity]:
        self.requested_subjects.append(identity_provider_subject)
        return self.events[offset : offset + limit]


@pytest.fixture
def settings() -> Settings:
    return Settings(
        service_name="customer-service",
        service_version="0.1.0",
        environment="test",
        log_level="WARNING",
        keycloak_issuer=TEST_ISSUER,
    )


@pytest.fixture
def database_engine(tmp_path: Path) -> Iterator[AsyncEngine]:
    database_path = tmp_path / "customer-test.db"
    database_url = os.getenv("TEST_DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    engine = create_async_engine(database_url)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    yield engine

    async def remove_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(remove_schema())


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def identity_activity_provider() -> StubIdentityActivityProvider:
    return StubIdentityActivityProvider()


@pytest.fixture
def token_factory(private_key: rsa.RSAPrivateKey) -> Any:
    def issue(
        *,
        subject: str = "keycloak-customer-a",
        roles: tuple[str, ...] = ("customer",),
        expires_in: timedelta = timedelta(minutes=5),
        audience: str = "shopsphere-api",
        signing_key: rsa.RSAPrivateKey | None = None,
        email: str | None = None,
        given_name: str = "Amina",
        family_name: str = "Khan",
    ) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": subject,
                "iss": TEST_ISSUER,
                "aud": audience,
                "iat": now,
                "exp": now + expires_in,
                "preferred_username": f"{subject}@example.test",
                "email": email or f"{subject}@example.test",
                "given_name": given_name,
                "family_name": family_name,
                "realm_access": {"roles": list(roles)},
            },
            signing_key or private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    return issue


@pytest.fixture
def client(
    settings: Settings,
    database_engine: AsyncEngine,
    private_key: rsa.RSAPrivateKey,
    identity_activity_provider: StubIdentityActivityProvider,
) -> Iterator[ApiClient]:
    verifier = KeycloakTokenVerifier(settings)
    verifier._keys = {"test-key": private_key.public_key()}
    verifier._keys_loaded_at = float("inf")
    application = create_app(
        settings,
        database_engine=database_engine,
        token_verifier=verifier,
        identity_activity_provider=identity_activity_provider,
    )
    yield ApiClient(application)


@pytest.fixture
def auth_headers(token_factory: Any) -> Any:
    def build(
        role: str = "customer",
        subject: str = "keycloak-customer-a",
        **identity_claims: Any,
    ) -> dict[str, str]:
        return {
            "Authorization": (
                f"Bearer {token_factory(subject=subject, roles=(role,), **identity_claims)}"
            )
        }

    return build
