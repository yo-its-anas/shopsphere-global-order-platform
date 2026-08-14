"""Environment-based service configuration without secret defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_SERVICE_NAME = "analytics-service"
DEFAULT_SERVICE_VERSION = "0.1.0"
_VALID_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"})


def _validate_origin(name: str, value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError(f"{name} must be a fixed HTTP(S) origin without credentials")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{name} contains an invalid port") from exc
    return value.rstrip("/")


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings safe to expose through service metadata."""

    service_name: str
    service_version: str
    environment: str
    log_level: str
    customer_service_url: str = "http://customer-service:8000"
    catalogue_service_url: str = "http://catalogue-service:8000"
    order_service_url: str = "http://order-service:8000"
    upstream_timeout_seconds: float = 5.0
    maximum_aggregate_records: int = 10_000
    keycloak_issuer: str | None = None
    keycloak_audience: str = "shopsphere-api"
    keycloak_role_client_id: str = "shopsphere-api"
    keycloak_jwks_url: str | None = None
    jwt_clock_skew_seconds: int = 30

    @classmethod
    def from_environment(cls) -> Settings:
        """Build settings from non-secret environment variables."""

        service_name = os.getenv("SERVICE_NAME", DEFAULT_SERVICE_NAME).strip()
        service_version = os.getenv("SERVICE_VERSION", DEFAULT_SERVICE_VERSION).strip()
        environment = os.getenv("APP_ENV", "development").strip()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        customer_service_url = os.getenv(
            "CUSTOMER_SERVICE_URL", "http://customer-service:8000"
        ).strip()
        catalogue_service_url = os.getenv(
            "CATALOGUE_SERVICE_URL", "http://catalogue-service:8000"
        ).strip()
        order_service_url = os.getenv("ORDER_SERVICE_URL", "http://order-service:8000").strip()
        keycloak_issuer = os.getenv("KEYCLOAK_ISSUER", "").strip().rstrip("/") or None
        keycloak_audience = os.getenv("KEYCLOAK_AUDIENCE", "shopsphere-api").strip()
        keycloak_role_client_id = os.getenv("KEYCLOAK_ROLE_CLIENT_ID", "shopsphere-api").strip()
        keycloak_jwks_url = os.getenv("KEYCLOAK_JWKS_URL", "").strip() or None

        try:
            upstream_timeout_seconds = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "5"))
            maximum_aggregate_records = int(os.getenv("MAXIMUM_AGGREGATE_RECORDS", "10000"))
            jwt_clock_skew_seconds = int(os.getenv("JWT_CLOCK_SKEW_SECONDS", "30"))
        except ValueError as exc:
            raise ValueError("Numeric configuration values are invalid") from exc

        if not service_name:
            raise ValueError("SERVICE_NAME must not be empty")
        if not service_version:
            raise ValueError("SERVICE_VERSION must not be empty")
        if not environment:
            raise ValueError("APP_ENV must not be empty")
        if log_level not in _VALID_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(_VALID_LOG_LEVELS)}")
        if not 0 < upstream_timeout_seconds <= 30:
            raise ValueError("UPSTREAM_TIMEOUT_SECONDS must be between 0 and 30")
        if not 100 <= maximum_aggregate_records <= 100_000:
            raise ValueError("MAXIMUM_AGGREGATE_RECORDS must be between 100 and 100000")
        if not keycloak_audience or not keycloak_role_client_id:
            raise ValueError("Keycloak audience and role client ID must not be empty")
        if not 0 <= jwt_clock_skew_seconds <= 120:
            raise ValueError("JWT_CLOCK_SKEW_SECONDS must be between 0 and 120")

        return cls(
            service_name=service_name,
            service_version=service_version,
            environment=environment,
            log_level=log_level,
            customer_service_url=_validate_origin("CUSTOMER_SERVICE_URL", customer_service_url),
            catalogue_service_url=_validate_origin("CATALOGUE_SERVICE_URL", catalogue_service_url),
            order_service_url=_validate_origin("ORDER_SERVICE_URL", order_service_url),
            upstream_timeout_seconds=upstream_timeout_seconds,
            maximum_aggregate_records=maximum_aggregate_records,
            keycloak_issuer=keycloak_issuer,
            keycloak_audience=keycloak_audience,
            keycloak_role_client_id=keycloak_role_client_id,
            keycloak_jwks_url=keycloak_jwks_url,
            jwt_clock_skew_seconds=jwt_clock_skew_seconds,
        )
