"""Structured JSON logging configuration."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.request_context import correlation_id
from app.core.telemetry import current_trace_fields

_LOG_RECORD_BUILTINS = frozenset(logging.makeLogRecord({}).__dict__)


class JsonFormatter(logging.Formatter):
    """Render one machine-readable JSON object per log record."""

    def __init__(self, service: str, version: str, environment: str) -> None:
        super().__init__()
        self._service = service
        self._version = version
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "version": self._version,
            "environment": self._environment,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get(),
            **current_trace_fields(),
        }

        for key, value in record.__dict__.items():
            if key not in _LOG_RECORD_BUILTINS and key not in {
                "message",
                "asctime",
                "trace_id",
                "span_id",
            }:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level_name: str, service: str, version: str, environment: str) -> None:
    """Configure application and Uvicorn loggers with the same JSON formatter."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service, version, environment))

    level = getattr(logging, level_name)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
