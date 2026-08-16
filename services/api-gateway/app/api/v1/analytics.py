"""Executive analytics capability routing."""

from __future__ import annotations

from fastapi import APIRouter, Path, Request
from starlette.responses import Response

from app.application.analytics_proxy import AnalyticsServiceProxy

router = APIRouter(tags=["Analytics capability"])


@router.get("/dashboard/{path:path}")
async def proxy_dashboard(
    request: Request,
    path: str = Path(..., description="The dashboard sub-path"),
) -> Response:
    proxy: AnalyticsServiceProxy = request.app.state.analytics_service_proxy
    return await proxy.forward(request, f"/api/v1/dashboard/{path}")

@router.get("/operations/{path:path}")
async def proxy_operations(
    request: Request,
    path: str = Path(..., description="The operations sub-path"),
) -> Response:
    proxy: AnalyticsServiceProxy = request.app.state.analytics_service_proxy
    return await proxy.forward(request, f"/api/v1/operations/{path}")
