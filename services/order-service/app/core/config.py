"""Environment-based service configuration without secret defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_SERVICE_NAME = "order-service"
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
    catalogue_service_url: str | None = None
    catalogue_timeout_seconds: float = 3.0
    service_token_url: str | None = None
    service_client_id: str | None = None
    service_client_secret: str | None = None
    kafka_bootstrap_servers: str | None = None
    kafka_client_id: str = "order-service-outbox"
    kafka_request_timeout_ms: int = 5000
    cart_currency_code: str = "USD"
    cart_max_item_quantity: int = 100

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
        catalogue_service_url = os.getenv("CATALOGUE_SERVICE_URL", "").strip().rstrip("/") or None
        service_token_url = os.getenv("SERVICE_TOKEN_URL", "").strip() or None
        service_client_id = os.getenv("SERVICE_CLIENT_ID", "").strip() or None
        service_client_secret = os.getenv("SERVICE_CLIENT_SECRET", "").strip() or None
        kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "").strip() or None
        kafka_client_id = os.getenv("KAFKA_CLIENT_ID", "order-service-outbox").strip()
        cart_currency_code = os.getenv("CART_CURRENCY_CODE", "USD").strip().upper()

        try:
            database_connect_timeout_seconds = float(
                os.getenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "3")
            )
            jwt_clock_skew_seconds = int(os.getenv("JWT_CLOCK_SKEW_SECONDS", "30"))
            catalogue_timeout_seconds = float(os.getenv("CATALOGUE_TIMEOUT_SECONDS", "3"))
            cart_max_item_quantity = int(os.getenv("CART_MAX_ITEM_QUANTITY", "100"))
            kafka_request_timeout_ms = int(os.getenv("KAFKA_REQUEST_TIMEOUT_MS", "5000"))
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
        if not 0 < database_connect_timeout_seconds <= 30:
            raise ValueError("DATABASE_CONNECT_TIMEOUT_SECONDS must be between 0 and 30")
        if not keycloak_audience or not keycloak_role_client_id:
            raise ValueError("Keycloak audience and role client ID must not be empty")
        if not 0 <= jwt_clock_skew_seconds <= 120:
            raise ValueError("JWT_CLOCK_SKEW_SECONDS must be between 0 and 120")
        if catalogue_service_url:
            parsed = urlsplit(catalogue_service_url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CATALOGUE_SERVICE_URL must be a fixed HTTP(S) service origin")
        if service_token_url:
            parsed_token_url = urlsplit(service_token_url)
            if (
                parsed_token_url.scheme not in {"http", "https"}
                or not parsed_token_url.hostname
                or parsed_token_url.username
                or parsed_token_url.password
                or parsed_token_url.query
                or parsed_token_url.fragment
            ):
                raise ValueError("SERVICE_TOKEN_URL must be a fixed HTTP(S) endpoint")
        service_credentials = (service_token_url, service_client_id, service_client_secret)
        if any(service_credentials) and not all(service_credentials):
            raise ValueError("All service identity settings must be supplied together")
        if not 0 < catalogue_timeout_seconds <= 30:
            raise ValueError("CATALOGUE_TIMEOUT_SECONDS must be between 0 and 30")
        if len(cart_currency_code) != 3 or not cart_currency_code.isalpha():
            raise ValueError("CART_CURRENCY_CODE must be a three-letter currency code")
        if not 1 <= cart_max_item_quantity <= 1000:
            raise ValueError("CART_MAX_ITEM_QUANTITY must be between 1 and 1000")
        if not kafka_client_id or not 1000 <= kafka_request_timeout_ms <= 30000:
            raise ValueError("Kafka client configuration is invalid")

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
            catalogue_service_url=catalogue_service_url,
            catalogue_timeout_seconds=catalogue_timeout_seconds,
            service_token_url=service_token_url,
            service_client_id=service_client_id,
            service_client_secret=service_client_secret,
            kafka_bootstrap_servers=kafka_bootstrap_servers,
            kafka_client_id=kafka_client_id,
            kafka_request_timeout_ms=kafka_request_timeout_ms,
            cart_currency_code=cart_currency_code,
            cart_max_item_quantity=cart_max_item_quantity,
        )
