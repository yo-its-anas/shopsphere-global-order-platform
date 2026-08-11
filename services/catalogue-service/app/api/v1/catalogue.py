"""Versioned Product Catalogue API routes."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, status

from app.api.dependencies import get_cache, get_catalogue_service, require_roles
from app.application.cache import (
    CacheBackend,
    cache_scope,
    get_cached_model,
    set_cached_model,
)
from app.application.catalogue import CatalogueService
from app.core.security import Principal, Role
from app.domain.models import Product, ProductCategory, ProductPrice, ProductStatus
from app.schemas.catalogue import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
    PriceListResponse,
    PriceResponse,
    PriceUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter()
catalogue_reader = require_roles(Role.CUSTOMER, Role.SUPPORT, Role.OPERATIONS_ADMIN)
operations_writer = require_roles(Role.OPERATIONS_ADMIN)
CatalogueReader = Annotated[Principal, Depends(catalogue_reader)]
OperationsWriter = Annotated[Principal, Depends(operations_writer)]
CatalogueApplication = Annotated[CatalogueService, Depends(get_catalogue_service)]
Cache = Annotated[CacheBackend, Depends(get_cache)]


def _request_id(request: Request) -> str:
    return str(request.state.correlation_id)


def _category_response(category: ProductCategory) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        is_active=category.is_active,
        parent_id=category.parent_id,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


def _product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        status=product.status,
        is_searchable=product.is_searchable,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _price_response(price: ProductPrice) -> PriceResponse:
    return PriceResponse(
        id=price.id,
        product_id=price.product_id,
        amount=price.amount,
        currency_code=price.currency_code,
        is_active=price.is_active,
        effective_from=price.effective_from,
        effective_to=price.effective_to,
        created_at=price.created_at,
        updated_at=price.updated_at,
    )


async def _invalidate_category_reads(request: Request, cache: CacheBackend) -> None:
    keys = request.app.state.cache_keys
    for family in (
        "category",
        "category-list",
        "product",
        "product-search",
        "availability",
    ):
        await cache.delete_prefix(keys.family_prefix(family), family=family)


async def _invalidate_product_reads(
    request: Request, cache: CacheBackend, product_id: UUID | None = None
) -> None:
    keys = request.app.state.cache_keys
    if product_id is not None:
        await cache.delete_prefix(keys.family_prefix("product"), family="product")
        await cache.delete_prefix(keys.family_prefix("availability"), family="availability")
    await cache.delete_prefix(keys.family_prefix("product-search"), family="product-search")


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Catalogue administration"],
    summary="Create a product category",
)
async def create_category(
    payload: CategoryCreate,
    request: Request,
    actor: OperationsWriter,
    service: CatalogueApplication,
    cache: Cache,
) -> CategoryResponse:
    category = await service.create_category(actor, payload.model_dump(), _request_id(request))
    await _invalidate_category_reads(request, cache)
    return _category_response(category)


@router.get(
    "/categories",
    response_model=CategoryListResponse,
    tags=["Catalogue queries"],
    summary="List product categories",
)
async def list_categories(
    request: Request,
    actor: CatalogueReader,
    service: CatalogueApplication,
    cache: Cache,
    active: Annotated[bool | None, Query()] = None,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CategoryListResponse:
    scope = cache_scope(actor.roles)
    key = request.app.state.cache_keys.category_list(scope, active, offset, limit)
    cached = await get_cached_model(cache, key, "category-list", CategoryListResponse)
    if cached is not None:
        return cached
    categories, total = await service.list_categories(actor, active, offset, limit)
    response = CategoryListResponse(
        items=[_category_response(category) for category in categories],
        offset=offset,
        limit=limit,
        total=total,
    )
    await set_cached_model(
        cache,
        key,
        "category-list",
        response,
        request.app.state.settings.category_cache_ttl_seconds,
    )
    return response


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    tags=["Catalogue queries"],
    summary="Retrieve a product category",
)
async def get_category(
    category_id: UUID,
    request: Request,
    actor: CatalogueReader,
    service: CatalogueApplication,
    cache: Cache,
) -> CategoryResponse:
    key = request.app.state.cache_keys.category(category_id, cache_scope(actor.roles))
    cached = await get_cached_model(cache, key, "category", CategoryResponse)
    if cached is not None:
        return cached
    response = _category_response(await service.get_category(actor, category_id))
    await set_cached_model(
        cache,
        key,
        "category",
        response,
        request.app.state.settings.category_cache_ttl_seconds,
    )
    return response


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    tags=["Catalogue administration"],
    summary="Update a product category",
)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    request: Request,
    actor: OperationsWriter,
    service: CatalogueApplication,
    cache: Cache,
) -> CategoryResponse:
    category = await service.update_category(
        actor,
        category_id,
        payload.model_dump(exclude_unset=True),
        _request_id(request),
    )
    await _invalidate_category_reads(request, cache)
    return _category_response(category)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Catalogue administration"],
    summary="Register a product",
)
async def create_product(
    payload: ProductCreate,
    request: Request,
    actor: OperationsWriter,
    service: CatalogueApplication,
    cache: Cache,
) -> ProductResponse:
    product = await service.create_product(actor, payload.model_dump(), _request_id(request))
    await _invalidate_product_reads(request, cache)
    return _product_response(product)


@router.get(
    "/products",
    response_model=ProductListResponse,
    tags=["Catalogue queries"],
    summary="Search and list products",
)
async def list_products(
    request: Request,
    actor: CatalogueReader,
    service: CatalogueApplication,
    cache: Cache,
    query: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    sku: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    product_status: Annotated[ProductStatus | None, Query(alias="status")] = None,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    sort_by: Annotated[Literal["created_at", "name", "sku", "updated_at"], Query()] = "name",
    sort_direction: Annotated[Literal["asc", "desc"], Query()] = "asc",
) -> ProductListResponse:
    key = request.app.state.cache_keys.product_search(
        {
            "scope": cache_scope(actor.roles),
            "query": query,
            "sku": sku.upper() if sku else None,
            "category_id": category_id,
            "status": product_status.value if product_status else None,
            "offset": offset,
            "limit": limit,
            "sort_by": sort_by,
            "sort_direction": sort_direction,
        }
    )
    cached = await get_cached_model(cache, key, "product-search", ProductListResponse)
    if cached is not None:
        return cached
    products, total = await service.list_products(
        actor,
        query=query,
        sku=sku,
        category_id=category_id,
        status=product_status,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    response = ProductListResponse(
        items=[_product_response(product) for product in products],
        offset=offset,
        limit=limit,
        total=total,
    )
    await set_cached_model(
        cache,
        key,
        "product-search",
        response,
        request.app.state.settings.search_cache_ttl_seconds,
    )
    return response


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    tags=["Catalogue queries"],
    summary="Retrieve a product",
)
async def get_product(
    product_id: UUID,
    request: Request,
    actor: CatalogueReader,
    service: CatalogueApplication,
    cache: Cache,
) -> ProductResponse:
    key = request.app.state.cache_keys.product(product_id, cache_scope(actor.roles))
    cached = await get_cached_model(cache, key, "product", ProductResponse)
    if cached is not None:
        return cached
    response = _product_response(await service.get_product(actor, product_id))
    await set_cached_model(
        cache,
        key,
        "product",
        response,
        request.app.state.settings.product_cache_ttl_seconds,
    )
    return response


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    tags=["Catalogue administration"],
    summary="Update a product",
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    request: Request,
    actor: OperationsWriter,
    service: CatalogueApplication,
    cache: Cache,
) -> ProductResponse:
    product = await service.update_product(
        actor,
        product_id,
        payload.model_dump(exclude_unset=True),
        _request_id(request),
    )
    await _invalidate_product_reads(request, cache, product_id)
    return _product_response(product)


@router.post(
    "/products/{product_id}/deactivate",
    response_model=ProductResponse,
    tags=["Catalogue administration"],
    summary="Deactivate a product",
)
async def deactivate_product(
    product_id: UUID,
    request: Request,
    actor: OperationsWriter,
    service: CatalogueApplication,
    cache: Cache,
) -> ProductResponse:
    product = await service.deactivate_product(actor, product_id, _request_id(request))
    await _invalidate_product_reads(request, cache, product_id)
    return _product_response(product)


@router.get(
    "/products/{product_id}/prices",
    response_model=PriceListResponse,
    tags=["Catalogue queries"],
    summary="Retrieve product pricing",
)
async def list_prices(
    product_id: UUID,
    request: Request,
    actor: CatalogueReader,
    service: CatalogueApplication,
    cache: Cache,
    include_history: Annotated[bool, Query()] = False,
) -> PriceListResponse:
    scope = cache_scope(actor.roles)
    key = request.app.state.cache_keys.prices(product_id, scope, include_history)
    cached = await get_cached_model(cache, key, "prices", PriceListResponse)
    if cached is not None:
        return cached
    prices = await service.list_prices(actor, product_id, include_history)
    response = PriceListResponse(items=[_price_response(price) for price in prices])
    await set_cached_model(
        cache,
        key,
        "prices",
        response,
        request.app.state.settings.price_cache_ttl_seconds,
    )
    return response


@router.put(
    "/products/{product_id}/prices/{currency_code}",
    response_model=PriceResponse,
    tags=["Catalogue administration"],
    summary="Set the immediately effective product price",
)
async def set_price(
    product_id: UUID,
    currency_code: Annotated[str, Path(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")],
    payload: PriceUpdate,
    request: Request,
    actor: OperationsWriter,
    service: CatalogueApplication,
    cache: Cache,
) -> PriceResponse:
    price = await service.set_price(
        actor,
        product_id,
        currency_code,
        payload.amount,
        _request_id(request),
    )
    await cache.delete_prefix(request.app.state.cache_keys.family_prefix("prices"), family="prices")
    return _price_response(price)
