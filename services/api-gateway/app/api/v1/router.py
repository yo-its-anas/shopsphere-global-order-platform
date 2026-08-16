"""Version 1 API composition."""

from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.catalogue import router as catalogue_router
from app.api.v1.customers import router as customer_router
from app.api.v1.info import router as info_router
from app.api.v1.orders import router as order_router

api_v1_router = APIRouter(prefix="/api/v1", tags=["Service information"])
api_v1_router.include_router(info_router)
api_v1_router.include_router(customer_router)
api_v1_router.include_router(catalogue_router)
api_v1_router.include_router(order_router)
api_v1_router.include_router(analytics_router)
