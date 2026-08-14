"""Gateway dependency composition."""

from typing import Annotated

from fastapi import Depends, Request

from app.application.catalogue_proxy import CatalogueServiceProxy
from app.application.customer_proxy import CustomerServiceProxy
from app.application.order_proxy import OrderServiceProxy


async def get_customer_proxy(request: Request) -> CustomerServiceProxy:
    return request.app.state.customer_service_proxy


CustomerProxy = Annotated[CustomerServiceProxy, Depends(get_customer_proxy)]


async def get_catalogue_proxy(request: Request) -> CatalogueServiceProxy:
    return request.app.state.catalogue_service_proxy


CatalogueProxy = Annotated[CatalogueServiceProxy, Depends(get_catalogue_proxy)]


async def get_order_proxy(request: Request) -> OrderServiceProxy:
    return request.app.state.order_service_proxy


OrderProxy = Annotated[OrderServiceProxy, Depends(get_order_proxy)]
