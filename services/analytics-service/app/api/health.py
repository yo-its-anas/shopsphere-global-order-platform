"""Kubernetes-compatible liveness and readiness endpoints."""

from fastapi import APIRouter, Request

from app.core.config import Settings
from app.schemas.system import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.get("/live", response_model=HealthResponse, summary="Check process liveness")
async def live(request: Request) -> HealthResponse:
    """Report that the API process can handle requests."""

    settings = _settings(request)
    return HealthResponse(
        status="alive",
        service=settings.service_name,
        version=settings.service_version,
    )


@router.get("/ready", response_model=HealthResponse, summary="Check service readiness")
async def ready(request: Request) -> HealthResponse:
    """Report readiness; no external dependencies are configured on Day 1."""

    settings = _settings(request)
    return HealthResponse(
        status="ready",
        service=settings.service_name,
        version=settings.service_version,
    )
