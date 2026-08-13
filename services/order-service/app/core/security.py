"""Keycloak-compatible bearer-token verification and role extraction."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Any, Protocol

import httpx2
import jwt
from jwt.exceptions import PyJWTError

from app.core.config import Settings
from app.core.errors import AuthenticationError, DependencyUnavailableError


class Role(str, Enum):
    CUSTOMER = "customer"
    SUPPORT = "support"
    OPERATIONS_ADMIN = "operations_admin"


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    username: str | None
    email: str | None
    roles: frozenset[str]

    def has_role(self, role: Role) -> bool:
        return role.value in self.roles


@dataclass(frozen=True, slots=True)
class AuthenticatedActor:
    principal: Principal
    access_token: str = field(repr=False)


class TokenVerifier(Protocol):
    def verify(self, token: str) -> Awaitable[Principal]: ...


class KeycloakTokenVerifier:
    def __init__(self, settings: Settings) -> None:
        if not settings.keycloak_issuer:
            raise ValueError("KEYCLOAK_ISSUER is required for JWT validation")
        self._issuer = settings.keycloak_issuer
        self._audience = settings.keycloak_audience
        self._role_client_id = settings.keycloak_role_client_id
        self._leeway = settings.jwt_clock_skew_seconds
        self._jwks_url = settings.keycloak_jwks_url or (
            f"{self._issuer}/protocol/openid-connect/certs"
        )
        self._keys: dict[str, Any] = {}
        self._keys_loaded_at = 0.0
        self._cache_seconds = 300
        self._refresh_lock = asyncio.Lock()

    async def verify(self, token: str) -> Principal:
        try:
            header = jwt.get_unverified_header(token)
            key_id = header.get("kid")
            if header.get("alg") != "RS256" or not isinstance(key_id, str):
                raise AuthenticationError
            signing_key = await self._get_signing_key(key_id)
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["sub", "iss", "aud", "exp"]},
            )
        except PyJWTError as exc:
            raise AuthenticationError from exc
        return _principal_from_claims(claims, self._role_client_id)

    async def _get_signing_key(self, key_id: str) -> Any:
        if key_id in self._keys and monotonic() - self._keys_loaded_at < self._cache_seconds:
            return self._keys[key_id]
        async with self._refresh_lock:
            if key_id in self._keys and monotonic() - self._keys_loaded_at < self._cache_seconds:
                return self._keys[key_id]
            try:
                async with httpx2.AsyncClient(timeout=5.0) as client:
                    response = await client.get(self._jwks_url)
                    response.raise_for_status()
                    document = response.json()
            except (httpx2.HTTPError, ValueError) as exc:
                raise DependencyUnavailableError from exc
            refreshed: dict[str, Any] = {}
            for key_document in document.get("keys", []) if isinstance(document, dict) else []:
                if not isinstance(key_document, dict):
                    continue
                candidate_id = key_document.get("kid")
                if isinstance(candidate_id, str) and key_document.get("kty") == "RSA":
                    try:
                        refreshed[candidate_id] = jwt.algorithms.RSAAlgorithm.from_jwk(key_document)
                    except (KeyError, TypeError, ValueError):
                        continue
            self._keys = refreshed
            self._keys_loaded_at = monotonic()
            if key_id not in self._keys:
                raise AuthenticationError
            return self._keys[key_id]


def _principal_from_claims(claims: dict[str, Any], role_client_id: str) -> Principal:
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise AuthenticationError
    realm_access = claims.get("realm_access", {})
    realm_roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
    resource_access = claims.get("resource_access", {})
    client_access = (
        resource_access.get(role_client_id, {}) if isinstance(resource_access, dict) else {}
    )
    client_roles = client_access.get("roles", []) if isinstance(client_access, dict) else []
    roles = frozenset(
        role
        for role in (*realm_roles, *client_roles)
        if isinstance(role, str) and role in {item.value for item in Role}
    )
    return Principal(
        subject=subject,
        username=(
            claims.get("preferred_username")
            if isinstance(claims.get("preferred_username"), str)
            else None
        ),
        email=claims.get("email") if isinstance(claims.get("email"), str) else None,
        roles=roles,
    )
