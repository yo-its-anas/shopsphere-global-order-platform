"""OpenTelemetry bootstrap and safe trace helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, SpanKind, Status, StatusCode, Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off", ""})
_EXCLUDED_SERVER_URLS = r"^/health/live$,^/health/ready$,^/metrics$"


class Telemetry:
    """Service-local tracing facade that never accepts sensitive span attributes."""

    def __init__(
        self,
        provider: SdkTracerProvider | None,
        service_name: str,
        *,
        owns_provider: bool = False,
    ) -> None:
        self._provider = provider
        self._owns_provider = owns_provider
        tracer_provider = provider or trace.NoOpTracerProvider()
        self.tracer: Tracer = tracer_provider.get_tracer(
            "shopsphere.telemetry",
            schema_url="https://opentelemetry.io/schemas/1.27.0",
        )

    @property
    def enabled(self) -> bool:
        return self._provider is not None

    def instrument_app(self, application: FastAPI) -> None:
        """Create server spans without capturing request or response headers."""

        if not self.enabled:
            return
        FastAPIInstrumentor.instrument_app(
            application,
            tracer_provider=self._provider,
            excluded_urls=_EXCLUDED_SERVER_URLS,
            exclude_spans=["receive", "send"],
        )

    def inject(self, headers: MutableMapping[str, str]) -> None:
        """Inject the active W3C trace context into an outbound header carrier."""

        if self.enabled:
            propagate.inject(headers)

    @contextmanager
    def client_span(
        self,
        name: str,
        *,
        upstream_service: str,
        method: str,
    ) -> Iterator[Span]:
        """Create one bounded client span with low-cardinality, non-sensitive attributes."""

        attributes: Mapping[str, str] = {
            "server.address": upstream_service,
            "http.request.method": method.upper(),
            "shopsphere.upstream.service": upstream_service,
        }
        with self._safe_span(name, SpanKind.CLIENT, attributes) as span:
            yield span

    @contextmanager
    def operation_span(self, name: str, operation: str) -> Iterator[Span]:
        """Trace a high-value application operation without entity identifiers."""

        with self._safe_span(
            name,
            SpanKind.INTERNAL,
            {"shopsphere.operation": operation},
        ) as span:
            yield span

    @contextmanager
    def _safe_span(
        self,
        name: str,
        kind: SpanKind,
        attributes: Mapping[str, Any],
    ) -> Iterator[Span]:
        with self.tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=dict(attributes),
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                yield span
            except BaseException:
                span.set_status(Status(StatusCode.ERROR))
                raise

    @staticmethod
    def set_http_status(span: Span, status_code: int) -> None:
        span.set_attribute("http.response.status_code", status_code)
        if status_code >= 500:
            span.set_status(Status(StatusCode.ERROR))

    def shutdown(self) -> None:
        if self._provider is not None and self._owns_provider:
            self._provider.shutdown()


def configure_telemetry(
    service_name: str,
    service_version: str,
    environment: str,
) -> Telemetry:
    """Build tracing from environment; disabled is the safe default."""

    enabled = _environment_boolean("TELEMETRY_ENABLED", default=False)
    sdk_disabled = _environment_boolean("OTEL_SDK_DISABLED", default=False)
    propagate.set_global_textmap(TraceContextTextMapPropagator())
    if not enabled or sdk_disabled:
        return Telemetry(None, service_name)

    if not (
        os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    ):
        raise ValueError("Telemetry is enabled but no OTLP Collector endpoint is configured")

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment.name": environment,
        }
    )
    provider = SdkTracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    return Telemetry(provider, service_name, owns_provider=True)


def current_trace_fields() -> dict[str, str | None]:
    """Return fixed-width identifiers for JSON logs, or nulls outside a trace."""

    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return {"trace_id": None, "span_id": None}
    return {
        "trace_id": f"{context.trace_id:032x}",
        "span_id": f"{context.span_id:016x}",
    }


def _environment_boolean(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().casefold()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean value")
