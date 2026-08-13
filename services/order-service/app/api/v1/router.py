"""Version 1 API composition."""

from fastapi import APIRouter

from app.api.v1.cart import router as cart_router
from app.api.v1.info import router as info_router
from app.api.v1.orders import router as orders_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(info_router)
api_v1_router.include_router(cart_router)
api_v1_router.include_router(orders_router)
