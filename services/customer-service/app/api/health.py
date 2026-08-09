"""Kubernetes-compatible liveness and readiness endpoints."""

from fastapi import APIRouter, Request, Response, status

from app.core.config import Settings
from app.infrastructure.database import database_is_ready
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
async def ready(request: Request, response: Response) -> HealthResponse:
    """Report whether the required customer database is reachable."""

    settings = _settings(request)
    ready_status = await database_is_ready(request.app.state.database_engine)
    if not ready_status:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ready" if ready_status else "not_ready",
        service=settings.service_name,
        version=settings.service_version,
    )
