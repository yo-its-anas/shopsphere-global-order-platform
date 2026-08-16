"""Trace/log correlation and safe-span contract for catalogue-service."""

import json
import logging

from opentelemetry.sdk.trace import TracerProvider

from app.core.logging import JsonFormatter
from app.core.telemetry import Telemetry


def test_inventory_operation_span_correlates_log_without_entity_identifiers() -> None:
    telemetry = Telemetry(TracerProvider(), "catalogue-service")
    with telemetry.operation_span("inventory.reserve", "inventory_reservation"):
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "reservation event", (), None)
        payload = json.loads(JsonFormatter().format(record))

    assert len(payload["trace_id"]) == 32
    assert len(payload["span_id"]) == 16
    assert "product_id" not in payload
