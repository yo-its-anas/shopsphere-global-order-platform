"""Version 1 API composition."""

from fastapi import APIRouter

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.info import router as info_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(info_router)
api_v1_router.include_router(dashboard_router)
