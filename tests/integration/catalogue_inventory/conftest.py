"""Fixtures for isolated simulated catalogue and inventory records."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from typing import Any

import pytest

from customer_identity.http import HttpClient, HttpResponse
from customer_identity.keycloak import KeycloakTestManager, TemporaryIdentity

from .config import CatalogueIntegrationConfig, IntegrationConfigurationError
from .platform import PlatformInspector


@dataclass(slots=True)
class CatalogueContext:
    config: CatalogueIntegrationConfig
    http: HttpClient
    keycloak: KeycloakTestManager
    identities: dict[str, TemporaryIdentity]
    products: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    def api(
        self,
        identity_name: str,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        request_id: str | None = None,
    ) -> HttpResponse:
        token = self.keycloak.acquire_user_token(self.identities[identity_name])
        return self.http.request(
            method,
            self.config.api(path),
            token=token.value,
            json_body=json_body,
            request_id=request_id,
        )

    def create_category(self) -> dict[str, Any]:
        suffix = secrets.token_hex(7)
        response = self.api(
            "operations_admin",
            "POST",
            "categories",
            json_body={
                "name": f"Simulated Integration Category {suffix}",
                "slug": f"integration-{suffix}",
                "description": "Synthetic integration-test category.",
            },
        )
        assert response.status == 201, response.safe_body()
        document = response.json()
        self.categories.append(document["id"])
        return document

    def create_product(
        self,
        category_id: str,
        *,
        status: str = "active",
        searchable: bool = True,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        suffix = secrets.token_hex(7).upper()
        response = self.api(
            "operations_admin",
            "POST",
            "products",
            json_body={
                "sku": f"IT-{suffix}",
                "name": f"Simulated Integration Product {suffix}",
                "description": "Synthetic integration-test product.",
                "category_id": category_id,
                "status": status,
                "is_searchable": searchable,
            },
            request_id=request_id,
        )
        assert response.status == 201, response.safe_body()
        document = response.json()
        self.products.append(document["id"])
        return document


@pytest.fixture(scope="session")
def catalogue_config() -> CatalogueIntegrationConfig:
    if os.getenv("SHOPSPHERE_RUN_CATALOGUE_INTEGRATION", "").casefold() != "true":
        pytest.skip(
            "Live catalogue integration tests require explicit "
            "SHOPSPHERE_RUN_CATALOGUE_INTEGRATION=true opt-in."
        )
    try:
        return CatalogueIntegrationConfig.from_environment()
    except IntegrationConfigurationError as error:
        pytest.fail(str(error), pytrace=False)


@pytest.fixture(scope="session")
def catalogue_context(catalogue_config: CatalogueIntegrationConfig) -> CatalogueContext:
    http = HttpClient()
    keycloak = KeycloakTestManager(catalogue_config, http)  # type: ignore[arg-type]
    identities: dict[str, TemporaryIdentity] = {}
    context = CatalogueContext(catalogue_config, http, keycloak, identities)
    try:
        for sequence, (name, role) in enumerate(
            {
                "customer": "customer",
                "support": "support",
                "operations_admin": "operations_admin",
            }.items(),
            start=20,
        ):
            identities[name] = keycloak.create_identity(role, sequence)
        yield context
    finally:
        cleanup_errors: list[str] = []
        for product_id in reversed(context.products):
            try:
                response = context.api(
                    "operations_admin", "POST", f"products/{product_id}/deactivate"
                )
                if response.status not in {200, 404, 409}:
                    cleanup_errors.append("product deactivation cleanup failed")
            except Exception:
                cleanup_errors.append(
                    "product deactivation cleanup encountered an exception"
                )
        for category_id in reversed(context.categories):
            try:
                response = context.api(
                    "operations_admin",
                    "PATCH",
                    f"categories/{category_id}",
                    json_body={"is_active": False},
                )
                if response.status not in {200, 404, 409}:
                    cleanup_errors.append("category cleanup failed")
            except Exception:
                cleanup_errors.append("category cleanup encountered an exception")
        for identity in reversed(list(identities.values())):
            try:
                keycloak.delete_identity(identity)
            except Exception:
                cleanup_errors.append("temporary Keycloak identity cleanup failed")
        if cleanup_errors:
            pytest.fail("; ".join(cleanup_errors), pytrace=False)


@pytest.fixture(scope="session")
def platform_inspector(
    catalogue_config: CatalogueIntegrationConfig,
) -> PlatformInspector:
    if not catalogue_config.platform_checks:
        pytest.skip(
            "Platform observation requires SHOPSPHERE_TEST_ENABLE_PLATFORM_CHECKS=true."
        )
    return PlatformInspector(catalogue_config.kube_context)
