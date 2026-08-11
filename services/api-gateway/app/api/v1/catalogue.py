"""Explicit versioned transport routes for Catalogue and Inventory."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Request
from starlette.responses import Response

from app.api.dependencies import CatalogueProxy

router = APIRouter(tags=["Catalogue capability"])
_PROXY_RESPONSES = {
    502: {"description": "Catalogue capability returned a transport failure."},
    503: {"description": "Catalogue capability is temporarily unavailable."},
    504: {"description": "Catalogue capability timed out."},
}
ProxyEndpoint = Callable[..., Awaitable[Response]]


async def categories(request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, "/api/v1/categories")


async def category(category_id: UUID, request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/categories/{category_id}")


async def products(request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, "/api/v1/products")


async def product(product_id: UUID, request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/products/{product_id}")


async def product_deactivation(
    product_id: UUID, request: Request, proxy: CatalogueProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/products/{product_id}/deactivate")


async def product_prices(product_id: UUID, request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/products/{product_id}/prices")


async def product_price(
    product_id: UUID,
    currency_code: Annotated[str, Path(pattern=r"^[A-Za-z]{3}$")],
    request: Request,
    proxy: CatalogueProxy,
) -> Response:
    return await proxy.forward(request, f"/api/v1/products/{product_id}/prices/{currency_code}")


async def inventory(request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, "/api/v1/inventory")


async def inventory_statistics(request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, "/api/v1/inventory/statistics")


async def inventory_product(product_id: UUID, request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/inventory/products/{product_id}")


async def inventory_availability(
    product_id: UUID, request: Request, proxy: CatalogueProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/inventory/products/{product_id}/availability")


async def inventory_initialization(
    product_id: UUID, request: Request, proxy: CatalogueProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/inventory/products/{product_id}/initialize")


async def inventory_adjustments(
    product_id: UUID, request: Request, proxy: CatalogueProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/inventory/products/{product_id}/adjustments")


async def inventory_settings(product_id: UUID, request: Request, proxy: CatalogueProxy) -> Response:
    return await proxy.forward(request, f"/api/v1/inventory/products/{product_id}/settings")


async def inventory_movements(
    product_id: UUID, request: Request, proxy: CatalogueProxy
) -> Response:
    return await proxy.forward(request, f"/api/v1/inventory/products/{product_id}/movements")


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


for method in ("GET", "POST"):
    _route(
        "/categories",
        categories,
        method,
        f"catalogue_categories_{method.casefold()}",
        "List categories" if method == "GET" else "Create a category",
    )

for method in ("GET", "PATCH"):
    _route(
        "/categories/{category_id}",
        category,
        method,
        f"catalogue_category_{method.casefold()}",
        "Retrieve a category" if method == "GET" else "Update a category",
    )

for method in ("GET", "POST"):
    _route(
        "/products",
        products,
        method,
        f"catalogue_products_{method.casefold()}",
        "Search and list products" if method == "GET" else "Register a product",
    )

for method in ("GET", "PATCH"):
    _route(
        "/products/{product_id}",
        product,
        method,
        f"catalogue_product_{method.casefold()}",
        "Retrieve a product" if method == "GET" else "Update a product",
    )

_route(
    "/products/{product_id}/deactivate",
    product_deactivation,
    "POST",
    "catalogue_product_deactivate_post",
    "Deactivate a product",
)
_route(
    "/products/{product_id}/prices",
    product_prices,
    "GET",
    "catalogue_product_prices_get",
    "Retrieve product pricing",
)
_route(
    "/products/{product_id}/prices/{currency_code}",
    product_price,
    "PUT",
    "catalogue_product_price_put",
    "Set an effective product price",
)
_route(
    "/inventory",
    inventory,
    "GET",
    "inventory_list_get",
    "List operational inventory",
)
_route(
    "/inventory/statistics",
    inventory_statistics,
    "GET",
    "inventory_statistics_get",
    "Retrieve calculated inventory statistics",
)
_route(
    "/inventory/products/{product_id}",
    inventory_product,
    "GET",
    "inventory_product_get",
    "Retrieve operational inventory for a product",
)
_route(
    "/inventory/products/{product_id}/availability",
    inventory_availability,
    "GET",
    "inventory_product_availability_get",
    "Retrieve safe product availability",
)
_route(
    "/inventory/products/{product_id}/initialize",
    inventory_initialization,
    "POST",
    "inventory_product_initialize_post",
    "Initialize product inventory",
)
_route(
    "/inventory/products/{product_id}/adjustments",
    inventory_adjustments,
    "POST",
    "inventory_product_adjustments_post",
    "Apply an auditable inventory adjustment",
)
_route(
    "/inventory/products/{product_id}/settings",
    inventory_settings,
    "PATCH",
    "inventory_product_settings_patch",
    "Update inventory control settings",
)
_route(
    "/inventory/products/{product_id}/movements",
    inventory_movements,
    "GET",
    "inventory_product_movements_get",
    "Retrieve inventory movement history",
)
