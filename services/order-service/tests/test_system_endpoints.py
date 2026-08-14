"""Tests for the complete foundation endpoint surface."""

from app.core.config import Settings
from app.main import create_app
from tests.conftest import ApiClient


def test_liveness_endpoint(client: ApiClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "live-test"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
        "service": "order-service",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"] == "live-test"


def test_readiness_endpoint(client: ApiClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "order-service",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"]


def test_readiness_reports_unconfigured_database(settings: Settings) -> None:
    response = ApiClient(create_app(settings)).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_versioned_info_endpoint(client: ApiClient) -> None:
    response = client.get("/api/v1/info", headers={"X-Request-ID": "info-test"})

    assert response.status_code == 200
    assert response.json() == {
        "service": "order-service",
        "version": "0.1.0",
        "environment": "test",
    }
    assert response.headers["X-Request-ID"] == "info-test"
