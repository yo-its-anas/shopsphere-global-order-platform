"""Environment-based service configuration without secret defaults."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_SERVICE_NAME = "catalogue-service"
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
    redis_url: str | None = None
    redis_password: str | None = None
    redis_connect_timeout_seconds: float = 0.5
    cache_key_prefix: str = "shopsphere:catalogue:v1"
    category_cache_ttl_seconds: int = 300
    product_cache_ttl_seconds: int = 180
    search_cache_ttl_seconds: int = 60
    price_cache_ttl_seconds: int = 120
    availability_cache_ttl_seconds: int = 15
    supported_currencies: frozenset[str] = frozenset(
        {"AED", "AUD", "CAD", "CNY", "EUR", "GBP", "INR", "JPY", "PKR", "USD"}
    )

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
        redis_url = os.getenv("REDIS_URL", "").strip().rstrip("/") or None
        redis_password = os.getenv("REDIS_PASSWORD", "").strip() or None
        cache_key_prefix = os.getenv("CACHE_KEY_PREFIX", "shopsphere:catalogue:v1").strip()
        currency_values = os.getenv(
            "SUPPORTED_CURRENCIES", "AED,AUD,CAD,CNY,EUR,GBP,INR,JPY,PKR,USD"
        )
        supported_currencies = frozenset(
            value.strip().upper() for value in currency_values.split(",") if value.strip()
        )

        try:
            database_connect_timeout_seconds = float(
                os.getenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "3")
            )
            jwt_clock_skew_seconds = int(os.getenv("JWT_CLOCK_SKEW_SECONDS", "30"))
            redis_connect_timeout_seconds = float(os.getenv("REDIS_CONNECT_TIMEOUT_SECONDS", "0.5"))
            category_cache_ttl_seconds = int(os.getenv("CATEGORY_CACHE_TTL_SECONDS", "300"))
            product_cache_ttl_seconds = int(os.getenv("PRODUCT_CACHE_TTL_SECONDS", "180"))
            search_cache_ttl_seconds = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "60"))
            price_cache_ttl_seconds = int(os.getenv("PRICE_CACHE_TTL_SECONDS", "120"))
            availability_cache_ttl_seconds = int(os.getenv("AVAILABILITY_CACHE_TTL_SECONDS", "15"))
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
        if redis_url:
            parsed_redis_url = urlsplit(redis_url)
            if parsed_redis_url.scheme not in {"redis", "rediss"} or not parsed_redis_url.hostname:
                raise ValueError("REDIS_URL must use redis:// or rediss:// with a host")
            if parsed_redis_url.username or parsed_redis_url.password:
                raise ValueError("Redis credentials must be supplied through REDIS_PASSWORD")
            if redis_password is None:
                raise ValueError("REDIS_PASSWORD is required when REDIS_URL is configured")
        if redis_connect_timeout_seconds <= 0 or redis_connect_timeout_seconds > 5:
            raise ValueError("REDIS_CONNECT_TIMEOUT_SECONDS must be between 0 and 5")
        if not re.fullmatch(r"[a-z0-9][a-z0-9:_-]{2,80}", cache_key_prefix):
            raise ValueError("CACHE_KEY_PREFIX contains unsupported characters")
        cache_ttls = (
            category_cache_ttl_seconds,
            product_cache_ttl_seconds,
            search_cache_ttl_seconds,
            price_cache_ttl_seconds,
            availability_cache_ttl_seconds,
        )
        if any(ttl < 1 or ttl > 3600 for ttl in cache_ttls):
            raise ValueError("Cache TTL values must be between 1 and 3600 seconds")
        if availability_cache_ttl_seconds > 60:
            raise ValueError("AVAILABILITY_CACHE_TTL_SECONDS must not exceed 60")
        if not supported_currencies or any(
            not re.fullmatch(r"[A-Z]{3}", value) for value in supported_currencies
        ):
            raise ValueError("SUPPORTED_CURRENCIES must contain comma-separated ISO-like codes")

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
            redis_url=redis_url,
            redis_password=redis_password,
            redis_connect_timeout_seconds=redis_connect_timeout_seconds,
            cache_key_prefix=cache_key_prefix,
            category_cache_ttl_seconds=category_cache_ttl_seconds,
            product_cache_ttl_seconds=product_cache_ttl_seconds,
            search_cache_ttl_seconds=search_cache_ttl_seconds,
            price_cache_ttl_seconds=price_cache_ttl_seconds,
            availability_cache_ttl_seconds=availability_cache_ttl_seconds,
            supported_currencies=supported_currencies,
        )
