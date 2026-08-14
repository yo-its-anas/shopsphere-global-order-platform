"""OpenTelemetry server, client, propagation, and logging contracts."""

import asyncio
import json
import logging

import httpx2
import pytest
from fastapi import FastAPI
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.core.logging import JsonFormatter
from app.core.telemetry import Telemetry, configure_telemetry
from app.infrastructure.http_client import ConfiguredHttpClient

TRACE_ID = "1234567890abcdef1234567890abcdef"
PARENT_SPAN_ID = "1234567890abcdef"
TRACEPARENT = f"00-{TRACE_ID}-{PARENT_SPAN_ID}-01"


def _telemetry() -> tuple[Telemetry, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return Telemetry(provider, "api-gateway"), exporter


def test_server_extracts_w3c_context_without_capturing_sensitive_headers() -> None:
    telemetry, exporter = _telemetry()
    application = FastAPI()

    @application.get("/widgets/{widget_id}")
    async def widget(widget_id: str) -> dict[str, str]:
        return {"widget_id": widget_id}

    telemetry.instrument_app(application)

    async def request() -> httpx2.Response:
        transport = httpx2.ASGITransport(app=application)
        async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(
                "/widgets/dynamic-value",
                headers={
                    "traceparent": TRACEPARENT,
                    "Authorization": "Bearer must-not-appear",
                },
            )

    response = asyncio.run(request())
    spans = exporter.get_finished_spans()
    server_span = next(span for span in spans if span.kind.name == "SERVER")

    assert response.status_code == 200
    assert f"{server_span.context.trace_id:032x}" == TRACE_ID
    serialized = repr(server_span.attributes)
    assert "must-not-appear" not in serialized
    assert "authorization" not in serialized.casefold()
    assert "dynamic-value" not in server_span.name


def test_bounded_client_injects_traceparent_and_correlates_json_log() -> None:
    telemetry, exporter = _telemetry()
    captured: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return httpx2.Response(200, json={"ready": True})

    client = ConfiguredHttpClient(
        "http://order-service:8000",
        1.0,
        telemetry,
        "order-service",
        transport=httpx2.MockTransport(handler),
    )
    parent = TraceContextTextMapPropagator().extract({"traceparent": TRACEPARENT})

    async def invoke() -> str:
        with telemetry.tracer.start_as_current_span("gateway request", context=parent):
            record = logging.LogRecord("test", logging.INFO, __file__, 1, "safe message", (), None)
            rendered = JsonFormatter().format(record)
            await client.request(
                "GET",
                "/api/v1/orders/me",
                headers={"Authorization": "Bearer must-not-appear"},
            )
            return rendered

    rendered = json.loads(asyncio.run(invoke()))
    asyncio.run(client.aclose())

    assert captured[0].headers["traceparent"].startswith(f"00-{TRACE_ID}-")
    assert rendered["trace_id"] == TRACE_ID
    assert len(rendered["span_id"]) == 16
    serialized = repr(exporter.get_finished_spans())
    assert "must-not-appear" not in serialized
    assert "/api/v1/orders/me" not in serialized


def test_enabled_telemetry_requires_an_explicit_collector_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEMETRY_ENABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    with pytest.raises(ValueError, match="Collector endpoint"):
        configure_telemetry("api-gateway", "0.1.0", "test")
