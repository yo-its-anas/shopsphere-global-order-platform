"""Bounded Prometheus metrics for the analytics HTTP and aggregation surfaces."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class AnalyticsMetrics:
    """Per-application registry avoids cross-test/global collector contamination."""

    def __init__(self, service: str, version: str, environment: str) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        common = (service, environment)
        self._service = service
        self._environment = environment
        self.requests = Counter(
            "shopsphere_http_requests",
            "Completed HTTP requests.",
            ("service", "environment", "method", "route", "status_class"),
            registry=self.registry,
        )
        self.duration = Histogram(
            "shopsphere_http_request_duration_seconds",
            "HTTP request duration in seconds.",
            ("service", "environment", "method", "route"),
            registry=self.registry,
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
        )
        self.in_progress = Gauge(
            "shopsphere_http_requests_in_progress",
            "HTTP requests currently in progress.",
            ("service", "environment"),
            registry=self.registry,
        )
        self.exceptions = Counter(
            "shopsphere_application_exceptions",
            "Application exceptions by bounded family.",
            ("service", "environment", "exception_family"),
            registry=self.registry,
        )
        self.aggregations = Counter(
            "shopsphere_dashboard_aggregations",
            "Dashboard aggregation responses by endpoint and data status.",
            ("service", "environment", "endpoint", "data_status"),
            registry=self.registry,
        )
        self.dependencies = Counter(
            "shopsphere_analytics_dependency_requests",
            "Analytics dependency results by fixed service and bounded result.",
            ("service", "environment", "dependency", "result"),
            registry=self.registry,
        )
        self.service_info = Gauge(
            "shopsphere_service_info",
            "Static service identity.",
            ("service", "version", "environment"),
            registry=self.registry,
        )
        self.service_info.labels(service, version, environment).set(1)
        self.in_progress.labels(*common).set(0)

    def observe_request(self, method: str, route: str, status: int, seconds: float) -> None:
        status_class = f"{status // 100}xx"
        labels = (self._service, self._environment, method, route)
        self.requests.labels(*labels, status_class).inc()
        self.duration.labels(*labels).observe(seconds)

    def request_started(self) -> None:
        self.in_progress.labels(self._service, self._environment).inc()

    def request_finished(self) -> None:
        self.in_progress.labels(self._service, self._environment).dec()

    def observe_exception(self, family: str) -> None:
        self.exceptions.labels(self._service, self._environment, family).inc()

    def observe_aggregation(self, endpoint: str, data_status: str) -> None:
        self.aggregations.labels(self._service, self._environment, endpoint, data_status).inc()

    def observe_dependency(self, dependency: str, result: str) -> None:
        self.dependencies.labels(self._service, self._environment, dependency, result).inc()
