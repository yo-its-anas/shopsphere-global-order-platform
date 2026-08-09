"""Strict environment contract for live customer capability integration tests."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


class IntegrationConfigurationError(RuntimeError):
    """Raised when live integration execution is requested without safe configuration."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value == "SET_IN_EXECUTION_ENVIRONMENT":
        raise IntegrationConfigurationError(f"Required environment variable {name} is missing.")
    return value


def _url(name: str) -> str:
    value = _required(name).rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise IntegrationConfigurationError(f"{name} must be a valid HTTP(S) URL.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise IntegrationConfigurationError(f"{name} must not contain credentials or query data.")
    return value


@dataclass(frozen=True, slots=True)
class IntegrationConfig:
    environment: str
    keycloak_url: str
    gateway_url: str
    realm: str
    oidc_client_id: str
    oidc_client_secret: str | None = field(repr=False)
    admin_client_id: str
    admin_client_secret: str = field(repr=False)
    maximum_expiry_wait_seconds: int
    jwt_clock_skew_seconds: int
    database_failure_readiness_url: str | None

    @classmethod
    def from_environment(cls) -> IntegrationConfig:
        if os.getenv("SHOPSPHERE_RUN_CUSTOMER_INTEGRATION", "").casefold() != "true":
            raise IntegrationConfigurationError(
                "Live execution requires SHOPSPHERE_RUN_CUSTOMER_INTEGRATION=true."
            )
        environment = _required("SHOPSPHERE_TEST_ENVIRONMENT").casefold()
        if environment not in {"test", "integration", "poc"}:
            raise IntegrationConfigurationError(
                "SHOPSPHERE_TEST_ENVIRONMENT must be test, integration, or poc."
            )
        if os.getenv("SHOPSPHERE_TEST_ALLOW_IDENTITY_MUTATION", "").casefold() != "true":
            raise IntegrationConfigurationError(
                "Temporary identity creation requires "
                "SHOPSPHERE_TEST_ALLOW_IDENTITY_MUTATION=true."
            )

        try:
            maximum_wait = int(os.getenv("SHOPSPHERE_TEST_MAX_EXPIRY_WAIT_SECONDS", "45"))
        except ValueError as error:
            raise IntegrationConfigurationError(
                "SHOPSPHERE_TEST_MAX_EXPIRY_WAIT_SECONDS must be an integer."
            ) from error
        try:
            clock_skew = int(os.getenv("SHOPSPHERE_TEST_JWT_CLOCK_SKEW_SECONDS", "30"))
        except ValueError as error:
            raise IntegrationConfigurationError(
                "SHOPSPHERE_TEST_JWT_CLOCK_SKEW_SECONDS must be an integer."
            ) from error
        if not 1 <= maximum_wait <= 60:
            raise IntegrationConfigurationError(
                "SHOPSPHERE_TEST_MAX_EXPIRY_WAIT_SECONDS must be between 1 and 60."
            )
        if not 0 <= clock_skew <= 120:
            raise IntegrationConfigurationError(
                "SHOPSPHERE_TEST_JWT_CLOCK_SKEW_SECONDS must be between 0 and 120."
            )

        failure_url_value = os.getenv("SHOPSPHERE_TEST_DATABASE_FAILURE_READINESS_URL", "").strip()
        if failure_url_value:
            parsed_failure_url = urlsplit(failure_url_value)
            if (
                parsed_failure_url.scheme not in {"http", "https"}
                or not parsed_failure_url.hostname
                or parsed_failure_url.username
                or parsed_failure_url.password
                or parsed_failure_url.query
                or parsed_failure_url.fragment
            ):
                raise IntegrationConfigurationError(
                    "SHOPSPHERE_TEST_DATABASE_FAILURE_READINESS_URL is invalid."
                )

        return cls(
            environment=environment,
            keycloak_url=_url("SHOPSPHERE_TEST_KEYCLOAK_URL"),
            gateway_url=_url("SHOPSPHERE_TEST_GATEWAY_URL"),
            realm=_required("SHOPSPHERE_TEST_REALM"),
            oidc_client_id=_required("SHOPSPHERE_TEST_OIDC_CLIENT_ID"),
            oidc_client_secret=(
                os.getenv("SHOPSPHERE_TEST_OIDC_CLIENT_SECRET", "").strip() or None
            ),
            admin_client_id=_required("SHOPSPHERE_TEST_ADMIN_CLIENT_ID"),
            admin_client_secret=_required("SHOPSPHERE_TEST_ADMIN_CLIENT_SECRET"),
            maximum_expiry_wait_seconds=maximum_wait,
            jwt_clock_skew_seconds=clock_skew,
            database_failure_readiness_url=failure_url_value.rstrip("/") or None,
        )

    def keycloak(self, path: str) -> str:
        return f"{self.keycloak_url}/{path.lstrip('/')}"

    def gateway(self, path: str) -> str:
        return f"{self.gateway_url}/{path.lstrip('/')}"
