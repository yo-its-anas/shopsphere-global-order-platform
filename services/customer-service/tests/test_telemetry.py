"""Trace/log correlation contract for customer-service."""

import json
import logging

from opentelemetry.sdk.trace import TracerProvider

from app.core.logging import JsonFormatter
from app.core.telemetry import Telemetry


def test_structured_log_contains_current_trace_and_span_identifiers() -> None:
    telemetry = Telemetry(TracerProvider(), "customer-service")
    with telemetry.operation_span("customer.profile.provision", "profile_provisioning"):
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "profile event", (), None)
        payload = json.loads(JsonFormatter().format(record))

    assert len(payload["trace_id"]) == 32
    assert len(payload["span_id"]) == 16
    assert payload["correlation_id"] == "unassigned"
