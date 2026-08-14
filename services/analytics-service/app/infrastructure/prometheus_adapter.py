"""Prometheus adapter for fetching operational metrics safely."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx2

from app.core.config import Settings
from app.schemas.operations import (
    AlertClassification,
    AvailabilityState,
    OperationalAlert,
    ServiceHealth,
)

logger = logging.getLogger(__name__)


class PrometheusAdapter:
    """Safe adapter for querying specific operational metrics from Prometheus."""

    def __init__(self, settings: Settings) -> None:
        self.prometheus_url = settings.prometheus_url
        self.timeout = settings.upstream_timeout_seconds
        self._client = httpx2.AsyncClient(timeout=self.timeout)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _query(self, query: str) -> list[dict[str, Any]]:
        """Execute a fixed PromQL query safely."""
        try:
            response = await self._client.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
            return []
        except httpx2.RequestError as exc:
            logger.error("prometheus_request_failed", extra={"error": str(exc)})
            return []
        except Exception as exc:
            logger.error("prometheus_query_failed", extra={"error": str(exc)})
            return []

    async def get_service_health(self) -> list[ServiceHealth]:
        """Fetch the health of core applications."""
        up_results = await self._query('up{job="shopsphere-applications"}')
        latency_results = await self._query(
            'histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds_bucket{job="shopsphere-applications"}[5m])))'
        )

        latency_map = {}
        for res in latency_results:
            service = res.get("metric", {}).get("service")
            val = res.get("value", [0, "0"])[1]
            if service and val != "NaN":
                try:
                    latency_map[service] = float(val) * 1000  # Convert to ms
                except ValueError:
                    pass

        health_list = []
        now = datetime.now(timezone.utc)

        # Expected core services
        core_services = ["api-gateway", "customer-service", "catalogue-service", "order-service"]
        found_services = set()

        for res in up_results:
            metric = res.get("metric", {})
            service = metric.get("service") or metric.get("app.kubernetes.io/name", "unknown")
            if service not in core_services:
                continue

            found_services.add(service)
            val = res.get("value", [0, "0"])[1]

            is_up = val == "1"
            latency = latency_map.get(service)

            if is_up:
                if latency and latency > 1000:
                    state = AvailabilityState.DEGRADED
                    status = "Service is up but responding slowly"
                else:
                    state = AvailabilityState.AVAILABLE
                    status = "Service is healthy"
            else:
                state = AvailabilityState.UNAVAILABLE
                status = "Service is down or unreachable"

            health_list.append(
                ServiceHealth(
                    service_name=service,
                    status=status,
                    availability_state=state,
                    latency_ms=latency,
                    last_evaluated_timestamp=now,
                )
            )

        # Add missing services as UNKNOWN/UNAVAILABLE
        for srv in set(core_services) - found_services:
            health_list.append(
                ServiceHealth(
                    service_name=srv,
                    status="Service metrics not found",
                    availability_state=AvailabilityState.UNKNOWN,
                    latency_ms=None,
                    last_evaluated_timestamp=now,
                )
            )

        return health_list

    async def get_system_performance(self) -> dict[str, float]:
        """Fetch overall request and error rates."""
        rate_results = await self._query(
            'sum(rate(http_requests_total{job="shopsphere-applications"}[1m]))'
        )
        error_results = await self._query(
            'sum(rate(http_requests_total{job="shopsphere-applications", status=~"5.."}[1m]))'
        )

        overall_rate = 0.0
        if rate_results:
            try:
                overall_rate = float(rate_results[0].get("value", [0, "0"])[1])
            except ValueError:
                pass

        overall_error_rate = 0.0
        if error_results:
            try:
                overall_error_rate = float(error_results[0].get("value", [0, "0"])[1])
            except ValueError:
                pass

        return {
            "overall_request_rate": overall_rate,
            "overall_error_rate": overall_error_rate,
        }

    async def get_active_alerts(self) -> list[OperationalAlert]:
        """Fetch active alerts mapped to executive operational alerts."""
        alerts = await self._query('ALERTS{alertstate="firing"}')
        operational_alerts = []

        for res in alerts:
            metric = res.get("metric", {})
            alertname = metric.get("alertname", "UnknownAlert")
            severity = metric.get("severity", "warning")
            category = metric.get("category", "application")
            service = metric.get("service")

            # Map category to classification
            classification = AlertClassification.APPLICATION
            if category == "infrastructure":
                classification = AlertClassification.INFRASTRUCTURE
            elif category == "business":
                classification = AlertClassification.BUSINESS

            operational_alerts.append(
                OperationalAlert(
                    alert_type=alertname,
                    classification=classification,
                    message=f"Active alert: {alertname} ({severity})",
                    service_name=service,
                    active_since=None,  # We don't have exact active_since from ALERTS query easily without ActiveAt
                )
            )

        return operational_alerts
