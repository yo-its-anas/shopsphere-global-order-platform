"""Authorized normalized activity visibility tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.errors import DependencyUnavailableError
from app.domain.models import (
    ActivityCategory,
    ActivityResult,
    ActivitySource,
    CustomerActivity,
)
from app.infrastructure.keycloak_activity import KeycloakIdentityActivityProvider


def _profile_payload() -> dict[str, str]:
    return {
        "first_name": "Amina",
        "last_name": "Khan",
        "email": "activity@example.test",
    }


def _identity_event() -> CustomerActivity:
    return CustomerActivity(
        timestamp=datetime(2026, 8, 8, 10, 30, tzinfo=timezone.utc),
        category=ActivityCategory.AUTHENTICATION,
        action="identity.login",
        source=ActivitySource.KEYCLOAK,
        result=ActivityResult.SUCCESS,
        context={"client_id": "shopsphere-frontend"},
    )


def test_customer_can_view_own_domain_and_identity_activity(
    client: Any, auth_headers: Any, identity_activity_provider: Any
) -> None:
    headers = auth_headers(subject="activity-customer")
    assert (
        client.post("/api/v1/customers/me", json=_profile_payload(), headers=headers).status_code
        == 201
    )
    identity_activity_provider.events = [_identity_event()]

    response = client.get("/api/v1/customers/me/activity?offset=0&limit=20", headers=headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["source"] for item in items} == {"customer_service", "keycloak"}
    assert identity_activity_provider.requested_subjects == ["activity-customer"]
    assert response.json()["offset"] == 0
    assert response.json()["limit"] == 20


def test_activity_access_requires_authentication_and_ownership(
    client: Any, auth_headers: Any
) -> None:
    customer = client.post(
        "/api/v1/customers/me",
        json=_profile_payload(),
        headers=auth_headers(subject="owner"),
    ).json()

    assert client.get("/api/v1/customers/me/activity").status_code == 401
    assert (
        client.get(
            f"/api/v1/admin/customers/{customer['id']}/activity",
            headers=auth_headers(subject="other-customer"),
        ).status_code
        == 403
    )


def test_support_and_operations_admin_can_view_customer_activity(
    client: Any, auth_headers: Any, identity_activity_provider: Any
) -> None:
    customer = client.post(
        "/api/v1/customers/me", json=_profile_payload(), headers=auth_headers()
    ).json()
    identity_activity_provider.events = [_identity_event()]
    url = f"/api/v1/admin/customers/{customer['id']}/activity"

    support = client.get(url, headers=auth_headers(role="support", subject="support-agent"))
    administrator = client.get(
        url,
        headers=auth_headers(role="operations_admin", subject="operations-administrator"),
    )

    assert support.status_code == 200
    assert administrator.status_code == 200
    assert any(item["action"] == "identity.login" for item in support.json()["items"])
    assert any(item["action"] == "profile.created" for item in administrator.json()["items"])


def test_keycloak_normalization_excludes_sensitive_raw_fields() -> None:
    raw = [
        {
            "time": 1786185000000,
            "type": "LOGIN_ERROR",
            "clientId": "shopsphere-frontend",
            "error": "invalid_user_credentials",
            "ipAddress": "198.51.100.7",
            "sessionId": "session-secret",
            "details": {
                "token_id": "token-secret",
                "password": "credential-secret",
                "refresh_token_id": "refresh-secret",
            },
        }
    ]

    normalized = KeycloakIdentityActivityProvider._normalize_user_events(raw)

    assert len(normalized) == 1
    assert normalized[0].action == "identity.login"
    assert normalized[0].result is ActivityResult.FAILURE
    assert normalized[0].context == {"client_id": "shopsphere-frontend"}
    rendered = repr(normalized[0])
    assert "token-secret" not in rendered
    assert "credential-secret" not in rendered
    assert "session-secret" not in rendered
    assert "198.51.100.7" not in rendered


def test_activity_pagination_is_applied_after_source_merge(
    client: Any, auth_headers: Any, identity_activity_provider: Any
) -> None:
    headers = auth_headers()
    client.post("/api/v1/customers/me", json=_profile_payload(), headers=headers)
    identity_activity_provider.events = [_identity_event()]

    first = client.get("/api/v1/customers/me/activity?offset=0&limit=1", headers=headers)
    second = client.get("/api/v1/customers/me/activity?offset=1&limit=1", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()["items"]) == 1
    assert len(second.json()["items"]) == 1
    assert first.json()["items"] != second.json()["items"]


def test_keycloak_unavailable_returns_safe_dependency_error(client: Any, auth_headers: Any) -> None:
    class UnavailableProvider:
        async def list_activity(
            self, identity_provider_subject: str, offset: int, limit: int
        ) -> list[CustomerActivity]:
            raise DependencyUnavailableError

    headers = auth_headers()
    client.post("/api/v1/customers/me", json=_profile_payload(), headers=headers)
    client.application.state.identity_activity_provider = UnavailableProvider()

    response = client.get("/api/v1/customers/me/activity", headers=headers)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dependency_unavailable"
    assert "Keycloak" not in response.text
    audit_history = client.get("/api/v1/customers/me/audit-history", headers=headers)
    assert audit_history.status_code == 200
    assert any(item["action"] == "profile.created" for item in audit_history.json()["items"])
