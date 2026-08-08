"""Registration-following profile provisioning and concurrency tests."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx2


def test_first_authenticated_request_provisions_profile_and_audit(
    client: Any, auth_headers: Any
) -> None:
    headers = {
        **auth_headers(
            subject="registered-customer",
            email="registered@example.test",
            given_name="Sara",
            family_name="Ahmed",
        ),
        "X-Request-ID": "registration-provisioning",
    }

    response = client.put("/api/v1/customers/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["provisioned"] is True
    assert response.json()["profile"]["email"] == "registered@example.test"
    assert response.json()["profile"]["first_name"] == "Sara"
    activity = client.get("/api/v1/customers/me/activity", headers=headers)
    provision_events = [
        event for event in activity.json()["items"] if event["action"] == "profile.provisioned"
    ]
    assert len(provision_events) == 1
    assert provision_events[0]["correlation_id"] == "registration-provisioning"
    assert provision_events[0]["metadata"] == {"source": "authenticated_identity"}


def test_subsequent_authentication_reuses_profile(client: Any, auth_headers: Any) -> None:
    first_headers = auth_headers(subject="returning-customer")
    first = client.put("/api/v1/customers/me", headers=first_headers)
    second_headers = auth_headers(subject="returning-customer")

    second = client.put("/api/v1/customers/me", headers=second_headers)

    assert first.json()["provisioned"] is True
    assert second.status_code == 200
    assert second.json()["provisioned"] is False
    assert second.json()["profile"]["id"] == first.json()["profile"]["id"]


def test_duplicate_provisioning_attempt_creates_one_profile_and_event(
    client: Any, auth_headers: Any
) -> None:
    headers = auth_headers(subject="duplicate-provisioning")

    results = [client.put("/api/v1/customers/me", headers=headers) for _ in range(3)]

    assert [result.json()["provisioned"] for result in results] == [True, False, False]
    assert len({result.json()["profile"]["id"] for result in results}) == 1
    activity = client.get("/api/v1/customers/me/activity", headers=headers).json()["items"]
    assert sum(event["action"] == "profile.provisioned" for event in activity) == 1


def test_changed_email_with_same_subject_does_not_create_or_rekey_profile(
    client: Any, auth_headers: Any
) -> None:
    original = client.put(
        "/api/v1/customers/me",
        headers=auth_headers(subject="stable-subject", email="original-address@example.test"),
    )

    repeated = client.put(
        "/api/v1/customers/me",
        headers=auth_headers(subject="stable-subject", email="changed-address@example.test"),
    )

    assert repeated.json()["provisioned"] is False
    assert repeated.json()["profile"]["id"] == original.json()["profile"]["id"]
    assert repeated.json()["profile"]["email"] == "original-address@example.test"


def test_concurrent_provisioning_attempts_converge_on_one_profile(
    client: Any, auth_headers: Any
) -> None:
    headers = auth_headers(subject="concurrent-customer")

    async def provision_concurrently() -> list[httpx2.Response]:
        transport = httpx2.ASGITransport(app=client.application)
        async with httpx2.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as async_client:
            return list(
                await asyncio.gather(
                    async_client.put("/api/v1/customers/me", headers=headers),
                    async_client.put("/api/v1/customers/me", headers=headers),
                )
            )

    responses = asyncio.run(provision_concurrently())

    assert all(response.status_code == 200 for response in responses)
    assert sorted(response.json()["provisioned"] for response in responses) == [False, True]
    assert len({response.json()["profile"]["id"] for response in responses}) == 1
    activity = client.get("/api/v1/customers/me/activity", headers=headers).json()["items"]
    assert sum(event["action"] == "profile.provisioned" for event in activity) == 1
