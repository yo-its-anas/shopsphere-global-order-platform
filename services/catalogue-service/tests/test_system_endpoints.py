"""Tests for the complete Day 1 endpoint surface."""

from fastapi.testclient import TestClient


def test_liveness_endpoint(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "live-test"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
        "service": "catalogue-service",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"] == "live-test"


def test_readiness_endpoint(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "catalogue-service",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"]


def test_versioned_info_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/info", headers={"X-Request-ID": "info-test"})

    assert response.status_code == 200
    assert response.json() == {
        "service": "catalogue-service",
        "version": "0.1.0",
        "environment": "test",
    }
    assert response.headers["X-Request-ID"] == "info-test"
