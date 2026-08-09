"""Live Customer Identity and Account Management integration coverage."""

from __future__ import annotations

import secrets
import time
from urllib.parse import quote

import pytest

from .conftest import IntegrationContext
from .http import assert_status

pytestmark = pytest.mark.customer_identity_integration


def test_keycloak_reachable_and_customer_registration_enabled(
    integration_context: IntegrationContext,
) -> None:
    context = integration_context
    discovery = context.http.request(
        "GET",
        context.config.keycloak(
            f"realms/{quote(context.config.realm)}/.well-known/openid-configuration"
        ),
    )
    assert_status(discovery, 200)
    document = discovery.json()
    assert document["issuer"].rstrip("/").endswith(f"/realms/{context.config.realm}")

    realm = context.keycloak.realm_document()
    assert realm.get("registrationAllowed") is True
    assert realm.get("enabled") is True
    assert set(context.identities) == {
        "customer_a",
        "customer_b",
        "support",
        "operations_admin",
    }


def test_complete_customer_profile_address_and_activity_flow(
    integration_context: IntegrationContext,
) -> None:
    context = integration_context
    acquired = context.keycloak.acquire_user_token(context.identities["customer_a"])
    assert acquired.expires_in > 0

    provisioned = context.provision("customer_a")
    assert_status(provisioned, 200)
    provisioned_document = provisioned.json()
    assert provisioned_document["provisioned"] is True
    profile_id = provisioned_document["profile"]["id"]

    repeated = context.provision("customer_a")
    assert_status(repeated, 200)
    assert repeated.json()["provisioned"] is False
    assert repeated.json()["profile"]["id"] == profile_id

    retrieved = context.api("customer_a", "GET", "customers/me")
    assert_status(retrieved, 200)
    assert retrieved.json()["id"] == profile_id
    assert retrieved.json()["email"].endswith("@example.invalid")

    updated = context.api(
        "customer_a",
        "PATCH",
        "customers/me",
        json_body={"first_name": "Simulated", "phone": "+92 300 0000001"},
        request_id="integration-profile-update",
    )
    assert_status(updated, 200)
    assert updated.json()["first_name"] == "Simulated"

    address = context.api(
        "customer_a",
        "POST",
        "customers/me/addresses",
        json_body={
            "label": "Integration Test Address",
            "recipient_name": "Simulated Customer",
            "line1": "100 Test Avenue",
            "line2": None,
            "city": "Test City",
            "region": "Test Region",
            "postal_code": "10000",
            "country_code": "PK",
            "phone": "+92 300 0000002",
            "is_default": True,
        },
        request_id="integration-address-create",
    )
    assert_status(address, 201)
    address_id = address.json()["id"]
    context.remember_address("customer_a", address_id)
    assert address.json()["is_default"] is True

    modified = context.api(
        "customer_a",
        "PATCH",
        f"customers/me/addresses/{address_id}",
        json_body={"city": "Updated Test City", "postal_code": "10001"},
        request_id="integration-address-update",
    )
    assert_status(modified, 200)
    assert modified.json()["city"] == "Updated Test City"

    listed = context.api("customer_a", "GET", "customers/me/addresses")
    assert_status(listed, 200)
    assert any(item["id"] == address_id for item in listed.json())

    audit = context.api("customer_a", "GET", "customers/me/audit-history?offset=0&limit=100")
    assert_status(audit, 200)
    audit_actions = {item["action"] for item in audit.json()["items"]}
    assert {
        "profile.provisioned",
        "profile.updated",
        "address.created",
        "address.updated",
    }.issubset(audit_actions)

    activity = context.api("customer_a", "GET", "customers/me/activity?offset=0&limit=100")
    assert_status(activity, 200)
    activity_actions = {item["action"] for item in activity.json()["items"]}
    assert "profile.updated" in activity_actions
    assert "address.updated" in activity_actions
    serialized_activity = str(activity.json()).casefold()
    assert "access_token" not in serialized_activity
    assert "refresh_token" not in serialized_activity
    assert "password" not in serialized_activity

    deleted = context.api("customer_a", "DELETE", f"customers/me/addresses/{address_id}")
    assert_status(deleted, 204)
    context.forget_address(address_id)


def test_rbac_support_and_operations_administrator_boundaries(
    integration_context: IntegrationContext,
) -> None:
    context = integration_context
    customer_profile = context.provision("customer_a").json()["profile"]

    listed = context.api("support", "GET", "admin/customers?offset=0&limit=100")
    assert_status(listed, 200)
    assert any(item["id"] == customer_profile["id"] for item in listed.json()["items"])

    support_view = context.api(
        "support", "GET", f"admin/customers/{customer_profile['id']}/activity"
    )
    assert_status(support_view, 200)
    support_mutation = context.api(
        "support",
        "PATCH",
        f"admin/customers/{customer_profile['id']}/status",
        json_body={"status": "suspended", "reason_code": "risk_review"},
    )
    assert_status(support_mutation, 403)

    customer_admin_attempt = context.api("customer_a", "GET", "admin/customers")
    assert_status(customer_admin_attempt, 403)

    suspended = context.api(
        "operations_admin",
        "PATCH",
        f"admin/customers/{customer_profile['id']}/status",
        json_body={"status": "suspended", "reason_code": "risk_review"},
        request_id="integration-operations-status",
    )
    assert_status(suspended, 200)
    assert suspended.json()["status"] == "suspended"
    reactivated = context.api(
        "operations_admin",
        "PATCH",
        f"admin/customers/{customer_profile['id']}/status",
        json_body={"status": "active", "reason_code": "administrative_correction"},
    )
    assert_status(reactivated, 200)


def test_unauthorized_and_invalid_tokens(
    integration_context: IntegrationContext,
) -> None:
    context = integration_context
    unauthorized = context.http.request("GET", context.config.gateway("customers/me"))
    assert_status(unauthorized, 401)

    invalid_bearer = f"not-a-jwt-{secrets.token_hex(8)}"
    invalid = context.http.request(
        "GET",
        context.config.gateway("customers/me"),
        token=invalid_bearer,
    )
    assert_status(invalid, 401)


def test_expired_token_is_rejected(
    integration_context: IntegrationContext,
) -> None:
    context = integration_context
    expiring = context.keycloak.acquire_user_token(context.identities["customer_a"])
    wait_seconds = expiring.expires_in + context.config.jwt_clock_skew_seconds + 1
    if wait_seconds > context.config.maximum_expiry_wait_seconds:
        pytest.skip(
            "The dedicated test client's token lifespan is too long for bounded expiration "
            "testing. Configure a short-lived integration client."
        )
    time.sleep(wait_seconds)
    expired = context.http.request(
        "GET", context.config.gateway("customers/me"), token=expiring.value
    )
    assert_status(expired, 401)


def test_cross_customer_idor_is_rejected(
    integration_context: IntegrationContext,
) -> None:
    context = integration_context
    context.provision("customer_a")
    second_profile = context.provision("customer_b").json()["profile"]
    second_address = context.api(
        "customer_b",
        "POST",
        "customers/me/addresses",
        json_body={
            "label": "Second Customer Test Address",
            "recipient_name": "Second Simulated Customer",
            "line1": "200 Isolation Street",
            "line2": None,
            "city": "Boundary City",
            "region": None,
            "postal_code": "20000",
            "country_code": "PK",
            "phone": None,
            "is_default": True,
        },
    )
    assert_status(second_address, 201)
    address_id = second_address.json()["id"]
    context.remember_address("customer_b", address_id)

    cross_address_update = context.api(
        "customer_a",
        "PATCH",
        f"customers/me/addresses/{address_id}",
        json_body={"city": "Unauthorized Change"},
    )
    assert_status(cross_address_update, 404)
    cross_admin_read = context.api("customer_a", "GET", f"admin/customers/{second_profile['id']}")
    assert_status(cross_admin_read, 403)


def test_database_connectivity_failure_readiness_is_safe_when_configured(
    integration_context: IntegrationContext,
) -> None:
    context = integration_context
    readiness_url = context.config.database_failure_readiness_url
    if not readiness_url:
        pytest.skip(
            "No isolated database-failure readiness endpoint was configured; the live PoC "
            "database is never disrupted by this suite."
        )
    response = context.http.request("GET", readiness_url)
    assert_status(response, 503)
    body = response.safe_body().casefold()
    assert "password" not in body
    assert "postgresql://" not in body
    assert "database_url" not in body
