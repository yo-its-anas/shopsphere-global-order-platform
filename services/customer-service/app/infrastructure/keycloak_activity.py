"""Least-privilege Keycloak Admin API adapter for safe customer activity."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx2

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError
from app.core.telemetry import Telemetry
from app.domain.models import (
    ActivityCategory,
    ActivityResult,
    ActivitySource,
    CustomerActivity,
)

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _identity_action(name: str) -> str:
    """Namespace a safe presentation label; values are event names, not credentials."""

    return f"identity.{name}"


_USER_EVENT_ACTIONS = {
    "LOGIN": "identity.login",
    "LOGIN_ERROR": "identity.login",
    "REGISTER": "identity.registration",
    "REGISTER_ERROR": "identity.registration",
    "LOGOUT": "identity.logout",
    "UPDATE_PASSWORD": _identity_action("credential_updated"),
    "UPDATE_PASSWORD_ERROR": _identity_action("credential_updated"),
    "SEND_RESET_PASSWORD": _identity_action("credential_reset_requested"),
    "RESET_PASSWORD": _identity_action("credential_reset"),
    "RESET_PASSWORD_ERROR": _identity_action("credential_reset"),
    "UPDATE_PROFILE": "identity.profile_updated",
    "UPDATE_PROFILE_ERROR": "identity.profile_updated",
    "UPDATE_EMAIL": "identity.email_updated",
    "UPDATE_EMAIL_ERROR": "identity.email_updated",
    "REFRESH_TOKEN": _identity_action("session_renewed"),
    "REFRESH_TOKEN_ERROR": _identity_action("session_renewed"),
}
_ADMIN_OPERATIONS = frozenset({"CREATE", "UPDATE", "DELETE", "ACTION"})


class KeycloakIdentityActivityProvider:
    """Fetch and normalize selected events without exposing raw Admin API documents."""

    def __init__(self, settings: Settings, telemetry: Telemetry | None = None) -> None:
        if not (
            settings.keycloak_issuer
            and settings.keycloak_admin_url
            and settings.keycloak_token_url
            and settings.keycloak_activity_client_id
            and settings.keycloak_activity_client_secret
        ):
            raise ValueError("Keycloak activity integration is not fully configured")
        # The OIDC issuer is a strict token claim and can be browser-facing, while this
        # back-channel endpoint must remain reachable from the service runtime.
        self._token_url = settings.keycloak_token_url
        realm = quote(settings.keycloak_activity_realm, safe="")
        self._events_url = f"{settings.keycloak_admin_url}/admin/realms/{realm}/events"
        self._admin_events_url = f"{settings.keycloak_admin_url}/admin/realms/{realm}/admin-events"
        self._client_id = settings.keycloak_activity_client_id
        self._client_secret = settings.keycloak_activity_client_secret
        self._timeout = settings.keycloak_activity_timeout_seconds
        self._telemetry = telemetry or Telemetry(None, "customer-service")

    async def list_activity(
        self, identity_provider_subject: str, offset: int, limit: int
    ) -> list[CustomerActivity]:
        """Return a safe merged projection of Keycloak user and user-admin events."""

        if not identity_provider_subject or len(identity_provider_subject) > 255:
            return []
        try:
            async with httpx2.AsyncClient(timeout=self._timeout) as client:
                access_token = await self._obtain_access_token(client)
                headers = {"Authorization": f"Bearer {access_token}"}
                self._telemetry.inject(headers)
                fetch_limit = offset + limit
                with self._telemetry.client_span(
                    "keycloak activity query",
                    upstream_service="keycloak",
                    method="GET",
                ) as span:
                    user_response = await client.get(
                        self._events_url,
                        headers=headers,
                        params={"user": identity_provider_subject, "first": 0, "max": fetch_limit},
                    )
                    admin_response = await client.get(
                        self._admin_events_url,
                        headers=headers,
                        params={
                            "resourcePath": f"users/{identity_provider_subject}",
                            "resourceTypes": "USER",
                            "first": 0,
                            "max": fetch_limit,
                        },
                    )
                    self._telemetry.set_http_status(span, admin_response.status_code)
                user_response.raise_for_status()
                admin_response.raise_for_status()
                user_document = user_response.json()
                admin_document = admin_response.json()
        except (httpx2.HTTPError, ValueError, TypeError) as exc:
            raise DependencyUnavailableError from exc

        user_events = self._normalize_user_events(user_document)
        admin_events = self._normalize_admin_events(admin_document)
        events = sorted(
            (*user_events, *admin_events), key=lambda item: item.timestamp, reverse=True
        )
        return events[offset : offset + limit]

    async def _obtain_access_token(self, client: httpx2.AsyncClient) -> str:
        headers: dict[str, str] = {}
        with self._telemetry.client_span(
            "keycloak service token",
            upstream_service="keycloak",
            method="POST",
        ) as span:
            self._telemetry.inject(headers)
            response = await client.post(
                self._token_url,
                headers=headers,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            self._telemetry.set_http_status(span, response.status_code)
        response.raise_for_status()
        document = response.json()
        token = document.get("access_token") if isinstance(document, dict) else None
        if not isinstance(token, str) or not token:
            raise ValueError("Keycloak token response did not contain an access token")
        return token

    @staticmethod
    def _timestamp(value: Any) -> datetime | None:
        if not isinstance(value, int) or value < 0:
            return None
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    @staticmethod
    def _safe_client_context(value: Any) -> dict[str, str]:
        if isinstance(value, str) and _SAFE_IDENTIFIER.fullmatch(value):
            return {"client_id": value}
        return {}

    @classmethod
    def _normalize_user_events(cls, document: Any) -> list[CustomerActivity]:
        if not isinstance(document, list):
            raise ValueError("Keycloak user event response must be a list")
        normalized: list[CustomerActivity] = []
        for raw in document:
            if not isinstance(raw, dict):
                continue
            event_type = raw.get("type")
            timestamp = cls._timestamp(raw.get("time"))
            action = _USER_EVENT_ACTIONS.get(event_type)
            if action is None or timestamp is None:
                continue
            normalized.append(
                CustomerActivity(
                    timestamp=timestamp,
                    category=ActivityCategory.AUTHENTICATION,
                    action=action,
                    source=ActivitySource.KEYCLOAK,
                    result=(
                        ActivityResult.FAILURE
                        if event_type.endswith("_ERROR") or raw.get("error")
                        else ActivityResult.SUCCESS
                    ),
                    context=cls._safe_client_context(raw.get("clientId")),
                )
            )
        return normalized

    @classmethod
    def _normalize_admin_events(cls, document: Any) -> list[CustomerActivity]:
        if not isinstance(document, list):
            raise ValueError("Keycloak admin event response must be a list")
        normalized: list[CustomerActivity] = []
        for raw in document:
            if not isinstance(raw, dict):
                continue
            operation = raw.get("operationType")
            resource_type = raw.get("resourceType")
            timestamp = cls._timestamp(raw.get("time"))
            if operation not in _ADMIN_OPERATIONS or resource_type != "USER" or timestamp is None:
                continue
            normalized.append(
                CustomerActivity(
                    timestamp=timestamp,
                    category=ActivityCategory.IDENTITY_ADMINISTRATION,
                    action=f"identity.administration.{operation.casefold()}",
                    source=ActivitySource.KEYCLOAK,
                    result=ActivityResult.SUCCESS,
                    context={"resource_type": "user"},
                )
            )
        return normalized
