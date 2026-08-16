"""Authorized executive business operations dashboard endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_dashboard_service, require_roles
from app.application.dashboard import DashboardService
from app.core.security import AuthenticatedActor, Role
from app.schemas.dashboard import (
    AlertsResponse,
    CustomerKpiResponse,
    ExecutiveSummaryResponse,
    InventoryKpiResponse,
    OperationsResponse,
    OrderKpiResponse,
)

router = APIRouter(prefix="/dashboard", tags=["Executive operations dashboard"])
OperationsActor = Annotated[AuthenticatedActor, Depends(require_roles(Role.OPERATIONS_ADMIN))]
OperationalReader = Annotated[
    AuthenticatedActor, Depends(require_roles(Role.SUPPORT, Role.OPERATIONS_ADMIN))
]
Dashboard = Annotated[DashboardService, Depends(get_dashboard_service)]


def _correlation_id(request: Request) -> str:
    return str(request.state.correlation_id)


@router.get("/summary", response_model=ExecutiveSummaryResponse)
async def summary(
    request: Request, actor: OperationsActor, dashboard: Dashboard
) -> ExecutiveSummaryResponse:
    with request.app.state.telemetry.operation_span(
        "analytics.dashboard.summary", "dashboard_aggregation"
    ):
        return await dashboard.summary(actor.access_token, _correlation_id(request))


@router.get("/orders", response_model=OrderKpiResponse)
async def orders(
    request: Request, actor: OperationsActor, dashboard: Dashboard
) -> OrderKpiResponse:
    return await dashboard.orders(actor.access_token, _correlation_id(request))


@router.get("/inventory", response_model=InventoryKpiResponse)
async def inventory(
    request: Request, actor: OperationalReader, dashboard: Dashboard
) -> InventoryKpiResponse:
    return await dashboard.inventory(actor.access_token, _correlation_id(request))


@router.get("/customers", response_model=CustomerKpiResponse)
async def customers(
    request: Request, actor: OperationalReader, dashboard: Dashboard
) -> CustomerKpiResponse:
    return await dashboard.customers(actor.access_token, _correlation_id(request))


@router.get("/operations", response_model=OperationsResponse)
async def operations(
    request: Request, _: OperationalReader, dashboard: Dashboard
) -> OperationsResponse:
    return await dashboard.operations(_correlation_id(request))


@router.get("/alerts", response_model=AlertsResponse)
async def alerts(
    request: Request, actor: OperationalReader, dashboard: Dashboard
) -> AlertsResponse:
    return await dashboard.alerts(actor.access_token, _correlation_id(request))
