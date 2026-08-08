"""Gateway dependency composition."""

from typing import Annotated

from fastapi import Depends, Request

from app.application.customer_proxy import CustomerServiceProxy


async def get_customer_proxy(request: Request) -> CustomerServiceProxy:
    return request.app.state.customer_service_proxy


CustomerProxy = Annotated[CustomerServiceProxy, Depends(get_customer_proxy)]
