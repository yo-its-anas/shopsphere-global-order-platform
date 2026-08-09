"""Live environment fixtures with explicit opt-in and bounded cleanup."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytest

from .config import IntegrationConfig, IntegrationConfigurationError
from .http import HttpClient, HttpResponse
from .keycloak import KeycloakTestManager, TemporaryIdentity


@dataclass(slots=True)
class IntegrationContext:
    config: IntegrationConfig
    http: HttpClient
    keycloak: KeycloakTestManager
    identities: dict[str, TemporaryIdentity]
    profile_ids: dict[str, str] = field(default_factory=dict)
    created_addresses: list[tuple[str, str]] = field(default_factory=list)

    def api(
        self,
        identity_name: str,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        request_id: str | None = None,
    ) -> HttpResponse:
        identity = self.identities[identity_name]
        token = self.keycloak.acquire_user_token(identity)
        return self.http.request(
            method,
            self.config.gateway(path),
            token=token.value,
            json_body=json_body,
            request_id=request_id,
        )

    def provision(self, identity_name: str) -> HttpResponse:
        response = self.api(identity_name, "PUT", "customers/me")
        if response.status == 200:
            document = response.json()
            self.profile_ids[identity_name] = document["profile"]["id"]
        return response

    def remember_address(self, identity_name: str, address_id: str) -> None:
        self.created_addresses.append((identity_name, address_id))

    def forget_address(self, address_id: str) -> None:
        self.created_addresses = [item for item in self.created_addresses if item[1] != address_id]


@pytest.fixture(scope="session")
def integration_config() -> IntegrationConfig:
    if os.getenv("SHOPSPHERE_RUN_CUSTOMER_INTEGRATION", "").casefold() != "true":
        pytest.skip(
            "Live customer integration tests require explicit "
            "SHOPSPHERE_RUN_CUSTOMER_INTEGRATION=true opt-in."
        )
    try:
        return IntegrationConfig.from_environment()
    except IntegrationConfigurationError as error:
        pytest.fail(str(error), pytrace=False)


@pytest.fixture(scope="session")
def integration_context(integration_config: IntegrationConfig) -> IntegrationContext:
    http = HttpClient()
    keycloak = KeycloakTestManager(integration_config, http)
    identities: dict[str, TemporaryIdentity] = {}
    context = IntegrationContext(integration_config, http, keycloak, identities)
    roles = {
        "customer_a": "customer",
        "customer_b": "customer",
        "support": "support",
        "operations_admin": "operations_admin",
    }
    try:
        for sequence, (name, role) in enumerate(roles.items(), start=1):
            identity = keycloak.create_identity(role, sequence)
            identities[name] = identity
        yield context
    finally:
        cleanup_errors: list[str] = []
        for identity_name, address_id in reversed(context.created_addresses):
            try:
                response = context.api(
                    identity_name,
                    "DELETE",
                    f"customers/me/addresses/{address_id}",
                )
                if response.status not in {204, 404, 409}:
                    cleanup_errors.append(f"address cleanup returned HTTP {response.status}")
            except Exception:  # cleanup must continue without printing credentials
                cleanup_errors.append("address cleanup encountered an exception")
        for identity in reversed(list(identities.values())):
            try:
                keycloak.delete_identity(identity)
            except Exception:
                cleanup_errors.append("temporary Keycloak identity cleanup failed")
        if cleanup_errors:
            pytest.fail("; ".join(cleanup_errors), pytrace=False)
