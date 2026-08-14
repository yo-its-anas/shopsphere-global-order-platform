"""Unit tests for operational visibility endpoints and services."""

from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.application.operations_service import OperationsService
from app.core.config import Settings
from app.infrastructure.prometheus_adapter import PrometheusAdapter
from app.schemas.operations import AlertClassification, AvailabilityState


@pytest.fixture
def mock_prometheus_adapter():
    adapter = MagicMock(spec=PrometheusAdapter)
    adapter.get_service_health = AsyncMock(return_value=[])
    adapter.get_system_performance = AsyncMock(
        return_value={"overall_request_rate": 0.0, "overall_error_rate": 0.0}
    )
    adapter.get_active_alerts = AsyncMock(return_value=[])
    return adapter


@pytest.fixture
def operations_service(mock_prometheus_adapter):
    return OperationsService(mock_prometheus_adapter)


@pytest.mark.anyio
async def test_prometheus_adapter_safe_queries(monkeypatch):
    """Test that the adapter executes only fixed safe queries."""
    settings = Settings(
        service_name="test", service_version="0.1.0", environment="test", log_level="INFO"
    )
    adapter = PrometheusAdapter(settings)

    mock_get = AsyncMock()
    # Mock httpx2.AsyncClient.get
    monkeypatch.setattr("httpx2.AsyncClient.get", mock_get)

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"status": "success", "data": {"result": []}}
    mock_get.return_value.raise_for_status = MagicMock()

    await adapter.get_service_health()

    # Verify fixed query is used
    calls = mock_get.call_args_list
    assert len(calls) == 2
    assert "up{job=" in calls[0].kwargs["params"]["query"]
    assert "histogram_quantile" in calls[1].kwargs["params"]["query"]


@pytest.mark.anyio
async def test_prometheus_adapter_unavailable(monkeypatch):
    """Test graceful handling when Prometheus is unavailable."""
    settings = Settings(
        service_name="test", service_version="0.1.0", environment="test", log_level="INFO"
    )
    adapter = PrometheusAdapter(settings)

    mock_get = AsyncMock()
    mock_get.side_effect = httpx2.RequestError("Connection failed")
    monkeypatch.setattr("httpx2.AsyncClient.get", mock_get)

    health = await adapter.get_service_health()
    # Should fall back to missing services -> UNKNOWN
    assert len(health) == 4
    for h in health:
        assert h.availability_state == AvailabilityState.UNKNOWN


@pytest.mark.anyio
async def test_operations_service_dashboard_healthy(mock_prometheus_adapter, operations_service):
    """Test dashboard compilation when all services are healthy."""
    from datetime import datetime, timezone

    from app.schemas.operations import ServiceHealth

    now = datetime.now(timezone.utc)
    mock_prometheus_adapter.get_service_health.return_value = [
        ServiceHealth(
            service_name="api-gateway",
            status="ok",
            availability_state=AvailabilityState.AVAILABLE,
            last_evaluated_timestamp=now,
        ),
        ServiceHealth(
            service_name="order-service",
            status="ok",
            availability_state=AvailabilityState.AVAILABLE,
            last_evaluated_timestamp=now,
        ),
    ]

    dashboard = await operations_service.get_dashboard()
    assert dashboard.system_performance.api_availability == 100.0
    assert dashboard.system_performance.healthy_service_count == 2
    assert dashboard.system_performance.degraded_service_count == 0
    assert dashboard.system_performance.unavailable_service_count == 0


@pytest.mark.anyio
async def test_operations_service_dashboard_degraded(mock_prometheus_adapter, operations_service):
    """Test dashboard compilation when one service is degraded."""
    from datetime import datetime, timezone

    from app.schemas.operations import ServiceHealth

    now = datetime.now(timezone.utc)
    mock_prometheus_adapter.get_service_health.return_value = [
        ServiceHealth(
            service_name="api-gateway",
            status="ok",
            availability_state=AvailabilityState.AVAILABLE,
            last_evaluated_timestamp=now,
        ),
        ServiceHealth(
            service_name="order-service",
            status="slow",
            availability_state=AvailabilityState.DEGRADED,
            last_evaluated_timestamp=now,
        ),
    ]

    dashboard = await operations_service.get_dashboard()
    # Availability counts degraded as "available but slow", so API availability is 100%
    assert dashboard.system_performance.api_availability == 100.0
    assert dashboard.system_performance.healthy_service_count == 1
    assert dashboard.system_performance.degraded_service_count == 1
    assert dashboard.system_performance.unavailable_service_count == 0


@pytest.mark.anyio
async def test_operations_service_active_alerts(mock_prometheus_adapter, operations_service):
    """Test active operational alerts are included."""
    from app.schemas.operations import OperationalAlert

    mock_prometheus_adapter.get_active_alerts.return_value = [
        OperationalAlert(
            alert_type="HighErrorRate",
            classification=AlertClassification.APPLICATION,
            message="High errors",
        )
    ]

    dashboard = await operations_service.get_dashboard()
    assert len(dashboard.active_alerts) == 1
    assert dashboard.active_alerts[0].alert_type == "HighErrorRate"


def test_api_operations_dashboard_unauthorized(client: TestClient):
    """Test unauthorized access to operations dashboard."""
    response = client.get("/api/v1/operations/dashboard")
    assert response.status_code == 401


def test_api_operations_dashboard_authorized(dashboard_client):
    """Test authorized access to operations dashboard."""
    OPS = {"Authorization": "Bearer operations-token"}
    response = dashboard_client.get("/api/v1/operations/dashboard", headers=OPS)
    # The adapter gets created inside the dependency but we don't strictly care about its real output for this integration test
    # unless it throws a 500, but we handle exceptions by returning empty/unknown.
    assert response.status_code == 200
    data = response.json()
    assert "services_health" in data
    assert "active_alerts" in data
    assert "system_performance" in data
