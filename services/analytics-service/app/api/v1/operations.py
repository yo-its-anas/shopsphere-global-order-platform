"""Executive operations visibility API endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import require_roles
from app.application.operations_service import OperationsService
from app.core.config import Settings
from app.core.security import AuthenticatedActor, Role
from app.infrastructure.prometheus_adapter import PrometheusAdapter
from app.schemas.operations import ExecutiveOperationsDashboard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["Executive operations dashboard"])


def get_prometheus_adapter(request: Request) -> PrometheusAdapter:
    """Dependency provider for PrometheusAdapter."""
    settings: Settings = request.app.state.settings
    if not hasattr(request.app.state, "prometheus_adapter"):
        request.app.state.prometheus_adapter = PrometheusAdapter(settings)
    return request.app.state.prometheus_adapter


AdapterDependency = Annotated[PrometheusAdapter, Depends(get_prometheus_adapter)]


def get_operations_service(
    adapter: AdapterDependency,
) -> OperationsService:
    """Dependency provider for OperationsService."""
    return OperationsService(prometheus_adapter=adapter)


OperationsServiceDependency = Annotated[OperationsService, Depends(get_operations_service)]
OperationsAdminToken = Annotated[AuthenticatedActor, Depends(require_roles(Role.OPERATIONS_ADMIN))]


@router.get(
    "/dashboard",
    response_model=ExecutiveOperationsDashboard,
    summary="Get operational visibility dashboard",
    description="Returns an aggregated, executive-level summary of service health, operational alerts, and system performance.",
)
async def get_operations_dashboard(
    operations_service: OperationsServiceDependency,
    token: OperationsAdminToken,
) -> ExecutiveOperationsDashboard:
    """Return the executive operations dashboard."""
    return await operations_service.get_dashboard()
