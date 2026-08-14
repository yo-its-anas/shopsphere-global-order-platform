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
    """Report whether all configured synchronous capabilities can accept traffic."""

    settings = _settings(request)
    request_id = str(request.state.correlation_id)
    customer_ready = await request.app.state.customer_service_proxy.is_ready(request_id)
    catalogue_ready = await request.app.state.catalogue_service_proxy.is_ready(request_id)
    order_ready = await request.app.state.order_service_proxy.is_ready(request_id)
    if not customer_ready or not catalogue_ready or not order_ready:
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
