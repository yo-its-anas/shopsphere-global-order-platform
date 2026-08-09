"""API tests for ownership, role policy, validation, and domain auditing."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import rsa


def profile_payload(email: str = "customer@example.test") -> dict[str, str]:
    return {
        "first_name": "Amina",
        "last_name": "Khan",
        "email": email,
        "phone": "+92 300 1234567",
    }


def address_payload(label: str = "Home", default: bool = False) -> dict[str, Any]:
    return {
        "label": label,
        "recipient_name": "Amina Khan",
        "line1": "42 Enterprise Avenue",
        "city": "Lahore",
        "region": "Punjab",
        "postal_code": "54000",
        "country_code": "pk",
        "phone": "+92 300 1234567",
        "is_default": default,
    }


def test_profile_create_retrieve_update_and_conflict(client: Any, auth_headers: Any) -> None:
    headers = auth_headers()
    created = client.post("/api/v1/customers/me", json=profile_payload(), headers=headers)

    assert created.status_code == 201
    assert created.json()["status"] == "active"
    assert "identity_provider_subject" not in created.json()
    customer_id = created.json()["id"]

    retrieved = client.get("/api/v1/customers/me", headers=headers)
    assert retrieved.status_code == 200
    assert retrieved.json()["id"] == customer_id

    updated = client.patch(
        "/api/v1/customers/me",
        json={"first_name": "Amna", "phone": None},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Amna"
    assert updated.json()["phone"] is None

    duplicate = client.post("/api/v1/customers/me", json=profile_payload(), headers=headers)
    assert duplicate.status_code == 409


def test_address_crud_default_selection_and_audit(client: Any, auth_headers: Any) -> None:
    headers = {**auth_headers(), "X-Request-ID": "address-workflow"}
    profile = client.post("/api/v1/customers/me", json=profile_payload(), headers=headers)
    assert profile.status_code == 201

    home = client.post("/api/v1/customers/me/addresses", json=address_payload(), headers=headers)
    assert home.status_code == 201
    assert home.json()["is_default"] is True

    office = client.post(
        "/api/v1/customers/me/addresses",
        json=address_payload("Office"),
        headers=headers,
    )
    office_id = office.json()["id"]
    assert office.json()["is_default"] is False

    selected = client.put(f"/api/v1/customers/me/addresses/{office_id}/default", headers=headers)
    assert selected.status_code == 200
    assert selected.json()["is_default"] is True

    updated = client.patch(
        f"/api/v1/customers/me/addresses/{office_id}",
        json={"city": "Islamabad"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Islamabad"

    listed = client.get("/api/v1/customers/me/addresses", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2
    assert listed.json()[0]["id"] == office_id

    deleted = client.delete(f"/api/v1/customers/me/addresses/{office_id}", headers=headers)
    assert deleted.status_code == 204
    remaining = client.get("/api/v1/customers/me/addresses", headers=headers).json()
    assert len(remaining) == 1
    assert remaining[0]["is_default"] is True

    activity = client.get("/api/v1/customers/me/activity", headers=headers)
    assert activity.status_code == 200
    actions = {event["action"] for event in activity.json()["items"]}
    assert {
        "profile.created",
        "address.created",
        "address.updated",
        "address.default_selected",
        "address.deleted",
    }.issubset(actions)
    assert any(
        event["context"].get("correlation_id") == "address-workflow"
        for event in activity.json()["items"]
    )


def test_authentication_failures(client: Any, token_factory: Any) -> None:
    assert client.get("/api/v1/customers/me").status_code == 401
    assert (
        client.get(
            "/api/v1/customers/me", headers={"Authorization": "Bearer malformed"}
        ).status_code
        == 401
    )
    expired = token_factory(expires_in=timedelta(minutes=-5))
    assert (
        client.get(
            "/api/v1/customers/me", headers={"Authorization": f"Bearer {expired}"}
        ).status_code
        == 401
    )
    wrong_audience = token_factory(audience="unrelated-client")
    assert (
        client.get(
            "/api/v1/customers/me",
            headers={"Authorization": f"Bearer {wrong_audience}"},
        ).status_code
        == 401
    )
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad_signature = token_factory(signing_key=other_key)
    assert (
        client.get(
            "/api/v1/customers/me",
            headers={"Authorization": f"Bearer {bad_signature}"},
        ).status_code
        == 401
    )


def test_customer_cannot_access_another_customer_or_admin_routes(
    client: Any, auth_headers: Any
) -> None:
    first_headers = auth_headers(subject="customer-a")
    first_profile = client.post(
        "/api/v1/customers/me",
        json=profile_payload("a@example.test"),
        headers=first_headers,
    ).json()
    address_id = client.post(
        "/api/v1/customers/me/addresses",
        json=address_payload(),
        headers=first_headers,
    ).json()["id"]

    second_headers = auth_headers(subject="customer-b")
    client.post(
        "/api/v1/customers/me",
        json=profile_payload("b@example.test"),
        headers=second_headers,
    )
    cross_customer = client.patch(
        f"/api/v1/customers/me/addresses/{address_id}",
        json={"city": "Karachi"},
        headers=second_headers,
    )
    assert cross_customer.status_code == 404

    admin_attempt = client.get(
        f"/api/v1/admin/customers/{first_profile['id']}", headers=second_headers
    )
    assert admin_attempt.status_code == 403


def test_support_is_read_only_and_can_view_activity(client: Any, auth_headers: Any) -> None:
    customer_headers = auth_headers()
    customer = client.post(
        "/api/v1/customers/me", json=profile_payload(), headers=customer_headers
    ).json()
    support_headers = auth_headers(role="support", subject="support-agent")

    listed = client.get("/api/v1/admin/customers", headers=support_headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == customer["id"]
    assert (
        client.get(
            f"/api/v1/admin/customers/{customer['id']}/activity",
            headers=support_headers,
        ).status_code
        == 200
    )
    modification = client.patch(
        f"/api/v1/admin/customers/{customer['id']}/status",
        json={"status": "suspended", "reason_code": "risk_review"},
        headers=support_headers,
    )
    assert modification.status_code == 403
    assert client.get("/api/v1/customers/me", headers=support_headers).status_code == 403


def test_operations_admin_changes_status_and_creates_audit_event(
    client: Any, auth_headers: Any
) -> None:
    customer_headers = auth_headers()
    customer = client.post(
        "/api/v1/customers/me", json=profile_payload(), headers=customer_headers
    ).json()
    admin_headers = {
        **auth_headers(role="operations_admin", subject="operations-admin"),
        "X-Request-ID": "admin-status-change",
    }

    changed = client.patch(
        f"/api/v1/admin/customers/{customer['id']}/status",
        json={"status": "suspended", "reason_code": "risk_review"},
        headers=admin_headers,
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "suspended"

    activity = client.get(
        f"/api/v1/admin/customers/{customer['id']}/activity", headers=admin_headers
    )
    status_event = next(
        item for item in activity.json()["items"] if item["action"] == "account.status_changed"
    )
    assert status_event["context"]["correlation_id"] == "admin-status-change"
    assert status_event["context"]["new_status"] == "suspended"
    assert status_event["context"]["reason_code"] == "risk_review"

    blocked_mutation = client.patch(
        "/api/v1/customers/me",
        json={"first_name": "Blocked"},
        headers=customer_headers,
    )
    assert blocked_mutation.status_code == 409


def test_input_and_pagination_validation(client: Any, auth_headers: Any) -> None:
    headers = auth_headers()
    invalid_profile = client.post(
        "/api/v1/customers/me",
        json={
            **profile_payload(),
            "email": "not-an-email",
            "password": "DoNotEchoCredentialValue42",
        },
        headers=headers,
    )
    assert invalid_profile.status_code == 422
    assert "DoNotEchoCredentialValue42" not in str(invalid_profile.json())

    valid_profile = client.post("/api/v1/customers/me", json=profile_payload(), headers=headers)
    assert valid_profile.status_code == 201
    invalid_address = client.post(
        "/api/v1/customers/me/addresses",
        json={**address_payload(), "country_code": "Pakistan"},
        headers=headers,
    )
    assert invalid_address.status_code == 422
    assert client.get("/api/v1/customers/me/activity?limit=101", headers=headers).status_code == 422
    immutable_identity_attempt = client.patch(
        "/api/v1/customers/me",
        json={"identity_provider_subject": "changed"},
        headers=headers,
    )
    assert immutable_identity_attempt.status_code == 422


def test_missing_customer_returns_not_found(client: Any, auth_headers: Any) -> None:
    assert client.get("/api/v1/customers/me", headers=auth_headers()).status_code == 404
    assert (
        client.get(
            f"/api/v1/admin/customers/{uuid4()}",
            headers=auth_headers(role="support", subject="support-agent"),
        ).status_code
        == 404
    )
