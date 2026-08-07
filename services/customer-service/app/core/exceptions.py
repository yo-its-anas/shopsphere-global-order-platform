"""Centralized HTTP exception responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", "unassigned"))


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return a consistent envelope for intentional HTTP failures."""

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"code": "http_error", "message": exc.detail},
            "correlation_id": _request_id(request),
        },
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return safe request-validation details."""

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "error": {"code": "validation_error", "details": exc.errors()},
                "correlation_id": _request_id(request),
            }
        ),
    )


async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures and avoid exposing internal exception details."""

    logger.exception(
        "unhandled_exception",
        exc_info=exc,
        extra={"event": "unhandled_exception"},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred.",
            },
            "correlation_id": _request_id(request),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the service-wide exception policy."""

    handlers: tuple[tuple[type[Exception], Any], ...] = (
        (HTTPException, http_exception_handler),
        (RequestValidationError, validation_exception_handler),
        (Exception, unexpected_exception_handler),
    )
    for exception_type, handler in handlers:
        app.add_exception_handler(exception_type, handler)
