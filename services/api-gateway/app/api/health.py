"""Kubernetes-compatible liveness and readiness endpoints."""

from fastapi import APIRouter, Request, Response, status

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
async def ready(request: Request, response: Response) -> HealthResponse:
    """Report whether the configured customer capability can accept traffic."""

    settings = _settings(request)
    if not await request.app.state.customer_service_proxy.is_ready(
        str(request.state.correlation_id)
    ):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="not_ready",
            service=settings.service_name,
            version=settings.service_version,
        )
    return HealthResponse(
        status="ready",
        service=settings.service_name,
        version=settings.service_version,
    )
