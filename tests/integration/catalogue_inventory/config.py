"""Validated environment contract for catalogue and inventory integration tests."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


class IntegrationConfigurationError(RuntimeError):
    """Raised when explicitly enabled tests lack safe configuration."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value == "SET_IN_EXECUTION_ENVIRONMENT":
        raise IntegrationConfigurationError(
            f"Required environment variable {name} is missing."
        )
    return value


def _optional_url(name: str) -> str | None:
    value = os.getenv(name, "").strip().rstrip("/")
    if not value:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise IntegrationConfigurationError(
            f"{name} must be an HTTP(S) URL without credentials, query data, or fragments."
        )
    return value


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().casefold() == "true"


@dataclass(frozen=True, slots=True)
class CatalogueIntegrationConfig:
    environment: str
    keycloak_url: str
    gateway_url: str | None
    service_url: str | None
    realm: str
    oidc_client_id: str
    oidc_client_secret: str | None = field(repr=False)
    admin_client_id: str
    admin_client_secret: str = field(repr=False)
    maximum_expiry_wait_seconds: int = 45
    jwt_clock_skew_seconds: int = 30
    platform_checks: bool = False
    redis_outage_test: bool = False
    kafka_outage_test: bool = False
    kube_context: str = "kind-shopsphere-poc"

    @classmethod
    def from_environment(cls) -> CatalogueIntegrationConfig:
        if not _enabled("SHOPSPHERE_RUN_CATALOGUE_INTEGRATION"):
            raise IntegrationConfigurationError(
                "Live execution requires SHOPSPHERE_RUN_CATALOGUE_INTEGRATION=true."
            )
        environment = _required("SHOPSPHERE_TEST_ENVIRONMENT").casefold()
        if environment not in {"test", "integration", "poc"}:
            raise IntegrationConfigurationError(
                "SHOPSPHERE_TEST_ENVIRONMENT must be test, integration, or poc."
            )
        if not _enabled("SHOPSPHERE_TEST_ALLOW_IDENTITY_MUTATION"):
            raise IntegrationConfigurationError(
                "Temporary test identities require "
                "SHOPSPHERE_TEST_ALLOW_IDENTITY_MUTATION=true."
            )

        gateway_url = _optional_url("SHOPSPHERE_CATALOGUE_GATEWAY_URL")
        if gateway_url is None:
            gateway_url = _optional_url("SHOPSPHERE_TEST_GATEWAY_URL")
        service_url = _optional_url("SHOPSPHERE_CATALOGUE_SERVICE_URL")
        if gateway_url is None and service_url is None:
            raise IntegrationConfigurationError(
                "Provide SHOPSPHERE_CATALOGUE_GATEWAY_URL or "
                "SHOPSPHERE_CATALOGUE_SERVICE_URL."
            )

        keycloak_url = _optional_url("SHOPSPHERE_TEST_KEYCLOAK_URL")
        if keycloak_url is None:
            raise IntegrationConfigurationError(
                "Required environment variable SHOPSPHERE_TEST_KEYCLOAK_URL is missing."
            )
        try:
            maximum_wait = int(
                os.getenv("SHOPSPHERE_TEST_MAX_EXPIRY_WAIT_SECONDS", "45")
            )
            clock_skew = int(os.getenv("SHOPSPHERE_TEST_JWT_CLOCK_SKEW_SECONDS", "30"))
        except ValueError as error:
            raise IntegrationConfigurationError(
                "JWT wait settings must be integers."
            ) from error
        if not 1 <= maximum_wait <= 60 or not 0 <= clock_skew <= 120:
            raise IntegrationConfigurationError(
                "JWT wait settings are outside safe bounds."
            )

        kube_context = os.getenv(
            "SHOPSPHERE_TEST_KUBE_CONTEXT", "kind-shopsphere-poc"
        ).strip()
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", kube_context):
            raise IntegrationConfigurationError(
                "SHOPSPHERE_TEST_KUBE_CONTEXT is invalid."
            )

        return cls(
            environment=environment,
            keycloak_url=keycloak_url,
            gateway_url=gateway_url,
            service_url=service_url,
            realm=_required("SHOPSPHERE_TEST_REALM"),
            oidc_client_id=_required("SHOPSPHERE_TEST_OIDC_CLIENT_ID"),
            oidc_client_secret=(
                os.getenv("SHOPSPHERE_TEST_OIDC_CLIENT_SECRET", "").strip() or None
            ),
            admin_client_id=_required("SHOPSPHERE_TEST_ADMIN_CLIENT_ID"),
            admin_client_secret=_required("SHOPSPHERE_TEST_ADMIN_CLIENT_SECRET"),
            maximum_expiry_wait_seconds=maximum_wait,
            jwt_clock_skew_seconds=clock_skew,
            platform_checks=_enabled("SHOPSPHERE_TEST_ENABLE_PLATFORM_CHECKS"),
            redis_outage_test=_enabled("SHOPSPHERE_TEST_ALLOW_REDIS_OUTAGE"),
            kafka_outage_test=_enabled("SHOPSPHERE_TEST_ALLOW_KAFKA_OUTAGE"),
            kube_context=kube_context,
        )

    @property
    def api_url(self) -> str:
        return self.gateway_url or str(self.service_url)

    @property
    def api_layer(self) -> str:
        return "gateway" if self.gateway_url else "service"

    def api(self, path: str) -> str:
        return f"{self.api_url}/{path.lstrip('/')}"

    def keycloak(self, path: str) -> str:
        return f"{self.keycloak_url}/{path.lstrip('/')}"
