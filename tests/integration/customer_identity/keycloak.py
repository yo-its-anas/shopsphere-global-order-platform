"""Least-privilege temporary identity and token operations for integration testing."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from .config import IntegrationConfig
from .http import HttpClient, assert_status


@dataclass(frozen=True, slots=True)
class TemporaryIdentity:
    user_id: str
    email: str
    password: str = field(repr=False)
    first_name: str
    last_name: str
    role: str


@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str = field(repr=False)
    expires_in: int


class KeycloakTestManager:
    def __init__(self, config: IntegrationConfig, http: HttpClient) -> None:
        self._config = config
        self._http = http
        self._admin_token: str | None = None

    def _service_token(self) -> str:
        if self._admin_token:
            return self._admin_token
        response = self._http.request(
            "POST",
            self._config.keycloak(
                f"realms/{quote(self._config.realm)}/protocol/openid-connect/token"
            ),
            form={
                "grant_type": "client_credentials",
                "client_id": self._config.admin_client_id,
                "client_secret": self._config.admin_client_secret,
            },
        )
        assert_status(response, 200)
        document = response.json()
        token = document.get("access_token") if isinstance(document, dict) else None
        assert isinstance(token, str) and token, "Keycloak returned no service access token."
        self._admin_token = token
        return token

    def realm_document(self) -> dict[str, Any]:
        response = self._http.request(
            "GET",
            self._config.keycloak(f"admin/realms/{quote(self._config.realm)}"),
            token=self._service_token(),
        )
        assert_status(response, 200)
        document = response.json()
        assert isinstance(document, dict)
        return document

    def create_identity(self, role: str, sequence: int) -> TemporaryIdentity:
        suffix = secrets.token_hex(8)
        email = f"shopsphere-it-{sequence}-{suffix}@example.invalid"
        password = f"It-{secrets.token_urlsafe(24)}-Aa1!"
        first_name = f"Integration{sequence}"
        last_name = "Customer"
        response = self._http.request(
            "POST",
            self._config.keycloak(f"admin/realms/{quote(self._config.realm)}/users"),
            token=self._service_token(),
            json_body={
                "username": email,
                "email": email,
                "emailVerified": True,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "credentials": [{"type": "password", "value": password, "temporary": False}],
                "attributes": {"shopsphere_test_identity": ["true"]},
            },
        )
        assert_status(response, 201)
        location = response.headers.get("Location") or response.headers.get("location")
        assert location, "Keycloak did not return the created user location."
        user_id = location.rstrip("/").rsplit("/", 1)[-1]
        identity = TemporaryIdentity(
            user_id=user_id,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        self.assign_realm_role(identity, role)
        return identity

    def assign_realm_role(self, identity: TemporaryIdentity, role: str) -> None:
        role_response = self._http.request(
            "GET",
            self._config.keycloak(f"admin/realms/{quote(self._config.realm)}/roles/{quote(role)}"),
            token=self._service_token(),
        )
        assert_status(role_response, 200)
        mapping_response = self._http.request(
            "POST",
            self._config.keycloak(
                f"admin/realms/{quote(self._config.realm)}/users/"
                f"{quote(identity.user_id)}/role-mappings/realm"
            ),
            token=self._service_token(),
            json_body=[role_response.json()],
        )
        assert_status(mapping_response, 204)

    def acquire_user_token(self, identity: TemporaryIdentity) -> AccessToken:
        form = {
            "grant_type": "password",
            "client_id": self._config.oidc_client_id,
            "username": identity.email,
            "password": identity.password,
            "scope": "openid profile email roles",
        }
        if self._config.oidc_client_secret:
            form["client_secret"] = self._config.oidc_client_secret
        response = self._http.request(
            "POST",
            self._config.keycloak(
                f"realms/{quote(self._config.realm)}/protocol/openid-connect/token"
            ),
            form=form,
        )
        assert_status(response, 200)
        document = response.json()
        token = document.get("access_token") if isinstance(document, dict) else None
        expires_in = document.get("expires_in") if isinstance(document, dict) else None
        assert isinstance(token, str) and token, "Keycloak returned no customer access token."
        assert isinstance(expires_in, int) and expires_in > 0
        return AccessToken(value=token, expires_in=expires_in)

    def delete_identity(self, identity: TemporaryIdentity) -> None:
        response = self._http.request(
            "DELETE",
            self._config.keycloak(
                f"admin/realms/{quote(self._config.realm)}/users/{quote(identity.user_id)}"
            ),
            token=self._service_token(),
        )
        assert response.status in {
            204,
            404,
        }, f"Temporary Keycloak identity cleanup failed with HTTP {response.status}."
