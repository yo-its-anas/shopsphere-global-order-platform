"""Explicit versioned transport routes for carts and order processing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request
from starlette.responses import Response

from app.api.dependencies import OrderProxy

router = APIRouter(tags=["Order capability"])
_PROXY_RESPONSES = {
    502: {"description": "Order capability returned a transport failure."},
    503: {"description": "Order capability is temporarily unavailable."},
    504: {"description": "Order capability timed out."},
}
ProxyEndpoint = Callable[..., Awaitable[Response]]


async def current_cart(request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, "/api/v1/carts/me")


async def cart_items(request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, "/api/v1/carts/me/items")


async def cart_item(item_id: UUID, request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/carts/me/items/{item_id}")


async def checkout(
    request: Request,
    proxy: OrderProxy,
    _idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Client-generated checkout retry key forwarded unchanged to order-service.",
        ),
    ] = None,
) -> Response:
    return await proxy.forward(request, "/api/v1/orders/checkout")


async def own_orders(request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, "/api/v1/orders/me")


async def own_order(order_id: UUID, request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/me/{order_id}")


async def own_order_history(order_id: UUID, request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/me/{order_id}/history")


async def own_order_audit(order_id: UUID, request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/me/{order_id}/audit")


async def own_order_cancellation(order_id: UUID, request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/me/{order_id}/cancellation")


async def administered_orders(request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, "/api/v1/orders/admin")


async def administered_order(order_id: UUID, request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/admin/{order_id}")


async def administered_order_history(
    order_id: UUID, request: Request, proxy: OrderProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/admin/{order_id}/history")


async def administered_order_audit(order_id: UUID, request: Request, proxy: OrderProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/admin/{order_id}/audit")


async def administered_order_status(
    order_id: UUID, request: Request, proxy: OrderProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/admin/{order_id}/status")


async def administered_order_cancellation(
    order_id: UUID, request: Request, proxy: OrderProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/orders/admin/{order_id}/cancellation")


def _route(
    path: str,
    endpoint: ProxyEndpoint,
    method: str,
    operation_id: str,
    summary: str,
) -> None:
    router.add_api_route(
        path,
        endpoint,
        methods=[method],
        responses=_PROXY_RESPONSES,
        operation_id=operation_id,
        summary=summary,
    )


_route("/carts/me", current_cart, "GET", "current_cart_get", "Retrieve the current cart")
_route("/carts/me/items", cart_items, "POST", "cart_item_post", "Add an item to the cart")
_route("/carts/me/items", cart_items, "DELETE", "cart_items_delete", "Clear the cart")
_route(
    "/carts/me/items/{item_id}",
    cart_item,
    "PATCH",
    "cart_item_patch",
    "Update a cart item quantity",
)
_route(
    "/carts/me/items/{item_id}",
    cart_item,
    "DELETE",
    "cart_item_delete",
    "Remove an item from the cart",
)
_route(
    "/orders/checkout",
    checkout,
    "POST",
    "order_checkout_post",
    "Checkout the authenticated customer's active cart",
)
_route("/orders/me", own_orders, "GET", "own_orders_get", "List the customer's orders")
_route("/orders/me/{order_id}", own_order, "GET", "own_order_get", "Retrieve an owned order")
_route(
    "/orders/me/{order_id}/history",
    own_order_history,
    "GET",
    "own_order_history_get",
    "Retrieve status history for an owned order",
)
_route(
    "/orders/me/{order_id}/audit",
    own_order_audit,
    "GET",
    "own_order_audit_get",
    "Retrieve safe audit history for an owned order",
)
_route(
    "/orders/me/{order_id}/cancellation",
    own_order_cancellation,
    "POST",
    "own_order_cancellation_post",
    "Cancel an eligible owned order",
)
_route(
    "/orders/admin",
    administered_orders,
    "GET",
    "administered_orders_get",
    "List orders for authorized support or operations",
)
_route(
    "/orders/admin/{order_id}",
    administered_order,
    "GET",
    "administered_order_get",
    "Retrieve an order for authorized support or operations",
)
_route(
    "/orders/admin/{order_id}/history",
    administered_order_history,
    "GET",
    "administered_order_history_get",
    "Retrieve order status history for authorized support or operations",
)
_route(
    "/orders/admin/{order_id}/audit",
    administered_order_audit,
    "GET",
    "administered_order_audit_get",
    "Retrieve order audit history for authorized support or operations",
)
_route(
    "/orders/admin/{order_id}/status",
    administered_order_status,
    "POST",
    "administered_order_status_post",
    "Apply an authorized administrative status transition",
)
_route(
    "/orders/admin/{order_id}/cancellation",
    administered_order_cancellation,
    "POST",
    "administered_order_cancellation_post",
    "Cancel an eligible order as an operations administrator",
)
