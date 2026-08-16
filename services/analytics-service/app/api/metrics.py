"""Internal Prometheus exposition endpoint."""

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["Observability"])


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    """Expose bounded application metrics for internal Prometheus scraping."""

    return Response(
        content=generate_latest(request.app.state.metrics.registry),
        media_type=CONTENT_TYPE_LATEST,
    )
