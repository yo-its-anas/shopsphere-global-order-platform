"""Environment-based service configuration without secret defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_SERVICE_NAME = "customer-service"
DEFAULT_SERVICE_VERSION = "0.1.0"
_VALID_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"})


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings safe to expose through service metadata."""

    service_name: str
    service_version: str
    environment: str
    log_level: str
    database_url: str | None = None
    database_connect_timeout_seconds: float = 3.0
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
        database_url = os.getenv("DATABASE_URL", "").strip() or None
        keycloak_issuer = os.getenv("KEYCLOAK_ISSUER", "").strip().rstrip("/") or None
        keycloak_audience = os.getenv("KEYCLOAK_AUDIENCE", "shopsphere-api").strip()
        keycloak_role_client_id = os.getenv("KEYCLOAK_ROLE_CLIENT_ID", "shopsphere-api").strip()
        keycloak_jwks_url = os.getenv("KEYCLOAK_JWKS_URL", "").strip() or None

        try:
            database_connect_timeout_seconds = float(
                os.getenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "3")
            )
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
        if database_connect_timeout_seconds <= 0 or database_connect_timeout_seconds > 30:
            raise ValueError("DATABASE_CONNECT_TIMEOUT_SECONDS must be between 0 and 30")
        if not keycloak_audience:
            raise ValueError("KEYCLOAK_AUDIENCE must not be empty")
        if not keycloak_role_client_id:
            raise ValueError("KEYCLOAK_ROLE_CLIENT_ID must not be empty")
        if jwt_clock_skew_seconds < 0 or jwt_clock_skew_seconds > 120:
            raise ValueError("JWT_CLOCK_SKEW_SECONDS must be between 0 and 120")

        return cls(
            service_name=service_name,
            service_version=service_version,
            environment=environment,
            log_level=log_level,
            database_url=database_url,
            database_connect_timeout_seconds=database_connect_timeout_seconds,
            keycloak_issuer=keycloak_issuer,
            keycloak_audience=keycloak_audience,
            keycloak_role_client_id=keycloak_role_client_id,
            keycloak_jwks_url=keycloak_jwks_url,
            jwt_clock_skew_seconds=jwt_clock_skew_seconds,
        )
