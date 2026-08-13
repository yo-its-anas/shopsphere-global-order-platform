"""Versioned service information endpoint."""

from fastapi import APIRouter, Request

from app.core.config import Settings
from app.schemas.system import ServiceInfoResponse

router = APIRouter(tags=["Service information"])


@router.get("/info", response_model=ServiceInfoResponse, summary="Describe this service")
async def info(request: Request) -> ServiceInfoResponse:
    """Return non-sensitive runtime identity metadata."""

    settings: Settings = request.app.state.settings
    return ServiceInfoResponse(
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment,
    )
