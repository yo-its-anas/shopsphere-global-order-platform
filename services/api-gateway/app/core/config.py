"""Environment-based service configuration without secret defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_SERVICE_NAME = "api-gateway"
DEFAULT_SERVICE_VERSION = "0.1.0"
_VALID_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"})
_DEFAULT_CORS_ORIGINS = ("http://localhost:5173",)


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings safe to expose through service metadata."""

    service_name: str
    service_version: str
    environment: str
    log_level: str
    customer_service_url: str = "http://customer-service:8000"
    customer_service_timeout_seconds: float = 5.0
    catalogue_service_url: str = "http://catalogue-service:8000"
    catalogue_service_timeout_seconds: float = 5.0
    cors_allowed_origins: tuple[str, ...] = _DEFAULT_CORS_ORIGINS

    @classmethod
    def from_environment(cls) -> Settings:
        """Build settings from non-secret environment variables."""

        service_name = os.getenv("SERVICE_NAME", DEFAULT_SERVICE_NAME).strip()
        service_version = os.getenv("SERVICE_VERSION", DEFAULT_SERVICE_VERSION).strip()
        environment = os.getenv("APP_ENV", "development").strip()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        customer_service_url = (
            os.getenv("CUSTOMER_SERVICE_URL", "http://customer-service:8000").strip().rstrip("/")
        )
        catalogue_service_url = (
            os.getenv("CATALOGUE_SERVICE_URL", "http://catalogue-service:8000").strip().rstrip("/")
        )
        cors_allowed_origins = tuple(
            origin.strip().rstrip("/")
            for origin in os.getenv("CORS_ALLOWED_ORIGINS", ",".join(_DEFAULT_CORS_ORIGINS)).split(
                ","
            )
            if origin.strip()
        )
        try:
            customer_service_timeout_seconds = float(
                os.getenv("CUSTOMER_SERVICE_TIMEOUT_SECONDS", "5")
            )
            catalogue_service_timeout_seconds = float(
                os.getenv("CATALOGUE_SERVICE_TIMEOUT_SECONDS", "5")
            )
        except ValueError as exc:
            raise ValueError("Upstream timeout values must be numeric") from exc

        if not service_name:
            raise ValueError("SERVICE_NAME must not be empty")
        if not service_version:
            raise ValueError("SERVICE_VERSION must not be empty")
        if not environment:
            raise ValueError("APP_ENV must not be empty")
        if log_level not in _VALID_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(_VALID_LOG_LEVELS)}")
        parsed_customer_url = urlsplit(customer_service_url)
        if (
            parsed_customer_url.scheme not in {"http", "https"}
            or not parsed_customer_url.hostname
            or parsed_customer_url.username
            or parsed_customer_url.password
            or parsed_customer_url.query
            or parsed_customer_url.fragment
            or parsed_customer_url.path not in {"", "/"}
        ):
            raise ValueError("CUSTOMER_SERVICE_URL must be an HTTP(S) origin without credentials")
        try:
            _ = parsed_customer_url.port
        except ValueError as exc:
            raise ValueError("CUSTOMER_SERVICE_URL contains an invalid port") from exc
        if customer_service_timeout_seconds <= 0 or customer_service_timeout_seconds > 30:
            raise ValueError("CUSTOMER_SERVICE_TIMEOUT_SECONDS must be between 0 and 30")
        parsed_catalogue_url = urlsplit(catalogue_service_url)
        if (
            parsed_catalogue_url.scheme not in {"http", "https"}
            or not parsed_catalogue_url.hostname
            or parsed_catalogue_url.username
            or parsed_catalogue_url.password
            or parsed_catalogue_url.query
            or parsed_catalogue_url.fragment
            or parsed_catalogue_url.path not in {"", "/"}
        ):
            raise ValueError("CATALOGUE_SERVICE_URL must be an HTTP(S) origin without credentials")
        try:
            _ = parsed_catalogue_url.port
        except ValueError as exc:
            raise ValueError("CATALOGUE_SERVICE_URL contains an invalid port") from exc
        if catalogue_service_timeout_seconds <= 0 or catalogue_service_timeout_seconds > 30:
            raise ValueError("CATALOGUE_SERVICE_TIMEOUT_SECONDS must be between 0 and 30")
        if not cors_allowed_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one explicit origin")
        for origin in cors_allowed_origins:
            parsed_origin = urlsplit(origin)
            if (
                origin == "*"
                or parsed_origin.scheme not in {"http", "https"}
                or not parsed_origin.hostname
                or parsed_origin.username
                or parsed_origin.password
                or parsed_origin.query
                or parsed_origin.fragment
                or parsed_origin.path not in {"", "/"}
            ):
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must contain explicit HTTP(S) origins without "
                    "credentials, paths, queries, or fragments"
                )

        return cls(
            service_name=service_name,
            service_version=service_version,
            environment=environment,
            log_level=log_level,
            customer_service_url=customer_service_url,
            customer_service_timeout_seconds=customer_service_timeout_seconds,
            catalogue_service_url=catalogue_service_url,
            catalogue_service_timeout_seconds=catalogue_service_timeout_seconds,
            cors_allowed_origins=cors_allowed_origins,
        )
