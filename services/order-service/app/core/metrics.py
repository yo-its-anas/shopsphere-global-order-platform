"""Bounded Prometheus metrics for Order Processing."""

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    GCCollector,
    Histogram,
    PlatformCollector,
    ProcessCollector,
)


class ServiceMetrics:
    def __init__(self, service: str, version: str, environment: str) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        ProcessCollector(registry=self.registry)
        PlatformCollector(registry=self.registry)
        GCCollector(registry=self.registry)
        self._common = (service, environment)
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
        )
        self.in_progress = Gauge(
            "shopsphere_http_requests_in_progress",
            "HTTP requests currently in progress.",
            ("service", "environment"),
            registry=self.registry,
        )
        self.service_info = Gauge(
            "shopsphere_service_info",
            "Static service identity.",
            ("service", "version", "environment"),
            registry=self.registry,
        )
        self.checkout_attempts = Counter(
            "shopsphere_order_checkout_attempts",
            "Checkout requests received.",
            ("service", "environment"),
            registry=self.registry,
        )
        self.checkout_results = Counter(
            "shopsphere_order_checkout_results",
            "Checkout outcomes.",
            ("service", "environment", "result"),
            registry=self.registry,
        )
        self.transitions = Counter(
            "shopsphere_order_transitions",
            "Administrative order transition outcomes.",
            ("service", "environment", "target_status", "result"),
            registry=self.registry,
        )
        self.service_info.labels(service, version, environment).set(1)
        self.in_progress.labels(*self._common).set(0)

    def request_started(self) -> None:
        self.in_progress.labels(*self._common).inc()

    def request_finished(self) -> None:
        self.in_progress.labels(*self._common).dec()

    def observe_request(self, method: str, route: str, status: int, seconds: float) -> None:
        labels = (*self._common, method, route)
        self.requests.labels(*labels, f"{status // 100}xx").inc()
        self.duration.labels(*labels).observe(seconds)

    def checkout_started(self) -> None:
        self.checkout_attempts.labels(*self._common).inc()

    def observe_checkout(self, result: str) -> None:
        self.checkout_results.labels(*self._common, result).inc()

    def observe_transition(self, target_status: str, result: str) -> None:
        self.transitions.labels(*self._common, target_status, result).inc()
