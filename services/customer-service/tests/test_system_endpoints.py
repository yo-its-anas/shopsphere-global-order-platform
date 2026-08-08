"""Tests for the complete foundation endpoint surface."""

from typing import Any


def test_liveness_endpoint(client: Any) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "live-test"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
        "service": "customer-service",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"] == "live-test"


def test_readiness_endpoint(client: Any) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "customer-service",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"]


def test_versioned_info_endpoint(client: Any) -> None:
    response = client.get("/api/v1/info", headers={"X-Request-ID": "info-test"})

    assert response.status_code == 200
    assert response.json() == {
        "service": "customer-service",
        "version": "0.1.0",
        "environment": "test",
    }
    assert response.headers["X-Request-ID"] == "info-test"


def test_readiness_reports_database_failure(client: Any, monkeypatch: object) -> None:
    async def unavailable(_: object) -> bool:
        return False

    monkeypatch.setattr("app.api.health.database_is_ready", unavailable)  # type: ignore[attr-defined]

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
