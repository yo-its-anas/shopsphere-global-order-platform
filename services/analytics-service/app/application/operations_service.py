"""Operational visibility application service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.infrastructure.prometheus_adapter import PrometheusAdapter
from app.schemas.operations import (
    AvailabilityState,
    ExecutiveOperationsDashboard,
    SystemPerformanceSummary,
)

logger = logging.getLogger(__name__)


class OperationsService:
    """Compiles the operational visibility dashboard using Prometheus data."""

    def __init__(self, prometheus_adapter: PrometheusAdapter) -> None:
        self.prometheus_adapter = prometheus_adapter

    async def get_dashboard(self) -> ExecutiveOperationsDashboard:
        """Compile and return the executive operations dashboard."""
        health = await self.prometheus_adapter.get_service_health()
        alerts = await self.prometheus_adapter.get_active_alerts()
        performance_data = await self.prometheus_adapter.get_system_performance()

        healthy_count = 0
        degraded_count = 0
        unavailable_count = 0

        for h in health:
            if h.availability_state == AvailabilityState.AVAILABLE:
                healthy_count += 1
            elif h.availability_state == AvailabilityState.DEGRADED:
                degraded_count += 1
            else:
                unavailable_count += 1

        total_services = len(health)
        api_availability = None
        if total_services > 0:
            api_availability = (healthy_count + degraded_count) / total_services * 100.0

        performance_summary = SystemPerformanceSummary(
            api_availability=api_availability,
            overall_request_rate=performance_data.get("overall_request_rate"),
            overall_error_rate=performance_data.get("overall_error_rate"),
            healthy_service_count=healthy_count,
            degraded_service_count=degraded_count,
            unavailable_service_count=unavailable_count,
        )

        return ExecutiveOperationsDashboard(
            services_health=health,
            active_alerts=alerts,
            system_performance=performance_summary,
            evaluated_at=datetime.now(timezone.utc),
        )
