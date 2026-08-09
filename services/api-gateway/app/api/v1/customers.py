"""Explicit versioned transport routes for the customer capability."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Request
from starlette.responses import Response

from app.api.dependencies import CustomerProxy

router = APIRouter(tags=["Customer capability"])
_PROXY_RESPONSES = {
    503: {"description": "Customer capability is temporarily unavailable."},
    504: {"description": "Customer capability timed out."},
}
ProxyEndpoint = Callable[..., Awaitable[Response]]


async def customer_profile(request: Request, proxy: CustomerProxy) -> Response:
    return await proxy.forward(request, "/api/v1/customers/me")


async def customer_addresses(request: Request, proxy: CustomerProxy) -> Response:
    return await proxy.forward(request, "/api/v1/customers/me/addresses")


async def customer_address(address_id: UUID, request: Request, proxy: CustomerProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/customers/me/addresses/{address_id}")


async def customer_default_address(
    address_id: UUID, request: Request, proxy: CustomerProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/customers/me/addresses/{address_id}/default")


async def customer_activity(request: Request, proxy: CustomerProxy) -> Response:
    return await proxy.forward(request, "/api/v1/customers/me/activity")


async def customer_audit_history(request: Request, proxy: CustomerProxy) -> Response:
    return await proxy.forward(request, "/api/v1/customers/me/audit-history")


async def customer_administration(request: Request, proxy: CustomerProxy) -> Response:
    return await proxy.forward(request, "/api/v1/admin/customers")


async def administered_customer(
    customer_id: UUID, request: Request, proxy: CustomerProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/admin/customers/{customer_id}")


async def administered_customer_activity(
    customer_id: UUID, request: Request, proxy: CustomerProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/admin/customers/{customer_id}/activity")


async def administered_customer_audit_history(
    customer_id: UUID, request: Request, proxy: CustomerProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/admin/customers/{customer_id}/audit-history")


async def administered_customer_status(
    customer_id: UUID, request: Request, proxy: CustomerProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/admin/customers/{customer_id}/status")


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


for method in ("GET", "POST", "PUT", "PATCH"):
    _route(
        "/customers/me",
        customer_profile,
        method,
        f"customer_profile_{method.casefold()}",
        "Access the authenticated customer's profile",
    )

for method in ("GET", "POST"):
    _route(
        "/customers/me/addresses",
        customer_addresses,
        method,
        f"customer_addresses_{method.casefold()}",
        "Access the authenticated customer's addresses",
    )

for method in ("PATCH", "DELETE"):
    _route(
        "/customers/me/addresses/{address_id}",
        customer_address,
        method,
        f"customer_address_{method.casefold()}",
        "Change an address owned by the authenticated customer",
    )

_route(
    "/customers/me/addresses/{address_id}/default",
    customer_default_address,
    "PUT",
    "customer_default_address_put",
    "Select the authenticated customer's default address",
)
_route(
    "/customers/me/activity",
    customer_activity,
    "GET",
    "customer_activity_get",
    "Retrieve normalized activity for the authenticated customer",
)
_route(
    "/customers/me/audit-history",
    customer_audit_history,
    "GET",
    "customer_audit_history_get",
    "Retrieve domain audit history for the authenticated customer",
)
_route(
    "/admin/customers",
    customer_administration,
    "GET",
    "customer_administration_get",
    "List customers for authorized support or operations",
)

for path, endpoint, operation_id, summary in (
    (
        "/admin/customers/{customer_id}",
        administered_customer,
        "administered_customer_get",
        "Retrieve a customer for authorized support or operations",
    ),
    (
        "/admin/customers/{customer_id}/activity",
        administered_customer_activity,
        "administered_customer_activity_get",
        "Retrieve normalized customer activity for authorized support or operations",
    ),
    (
        "/admin/customers/{customer_id}/audit-history",
        administered_customer_audit_history,
        "administered_customer_audit_history_get",
        "Retrieve customer-domain audit history for authorized support or operations",
    ),
):
    _route(path, endpoint, "GET", operation_id, summary)

_route(
    "/admin/customers/{customer_id}/status",
    administered_customer_status,
    "PATCH",
    "administered_customer_status_patch",
    "Change customer status as an authorized operations administrator",
)
