"""Trace/log correlation contract for analytics-service."""

import json
import logging

from opentelemetry.sdk.trace import TracerProvider

from app.core.logging import JsonFormatter
from app.core.telemetry import Telemetry


def test_dashboard_operation_span_correlates_structured_log() -> None:
    telemetry = Telemetry(TracerProvider(), "analytics-service")
    with telemetry.operation_span("analytics.dashboard.summary", "dashboard_aggregation"):
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "aggregation event", (), None)
        payload = json.loads(JsonFormatter("analytics-service", "0.1.0", "test").format(record))

    assert len(payload["trace_id"]) == 32
    assert len(payload["span_id"]) == 16
    assert payload["service"] == "analytics-service"
