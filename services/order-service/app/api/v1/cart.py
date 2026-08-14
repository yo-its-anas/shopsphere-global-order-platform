"""Authenticated customer shopping-cart routes."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_cart_service, get_customer_actor
from app.application.cart import CartService
from app.core.security import AuthenticatedActor
from app.domain.models import CartItem, ShoppingCart
from app.schemas.cart import (
    CartItemCreate,
    CartItemQuantityUpdate,
    CartItemResponse,
    ShoppingCartResponse,
)

router = APIRouter(prefix="/carts/me", tags=["Customer shopping cart"])
CustomerActor = Annotated[AuthenticatedActor, Depends(get_customer_actor)]
CartApplication = Annotated[CartService, Depends(get_cart_service)]


def _request_id(request: Request) -> str:
    return str(request.state.correlation_id)


def _response(
    cart: ShoppingCart, items: list[CartItem] | tuple[CartItem, ...]
) -> ShoppingCartResponse:
    item_responses = [
        CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            display_sku=item.display_sku,
            display_name=item.display_name,
            display_unit_price=item.display_unit_price,
            display_currency_code=item.display_currency_code,
            display_quantity_available=item.display_quantity_available,
            display_line_subtotal=item.display_line_subtotal,
            snapshot_at=item.snapshot_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]
    return ShoppingCartResponse(
        id=cart.id,
        status=cart.status.value,
        currency_code=cart.currency_code,
        version=cart.version,
        items=item_responses,
        item_count=sum(item.quantity for item in items),
        display_subtotal=sum(
            (item.display_line_subtotal for item in items), start=Decimal("0.0000")
        ),
        created_at=cart.created_at,
        updated_at=cart.updated_at,
    )


@router.get(
    "",
    response_model=ShoppingCartResponse,
    summary="Get or create the authenticated customer's active cart",
)
async def get_current_cart(actor: CustomerActor, service: CartApplication) -> ShoppingCartResponse:
    cart, items = await service.get_current(actor.principal.subject)
    return _response(cart, list(items))


@router.post(
    "/items",
    response_model=ShoppingCartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a validated product to the current cart",
)
async def add_cart_item(
    payload: CartItemCreate,
    request: Request,
    actor: CustomerActor,
    service: CartApplication,
) -> ShoppingCartResponse:
    cart, items = await service.add_item(
        actor.principal.subject,
        payload.product_id,
        payload.quantity,
        actor.access_token,
        _request_id(request),
    )
    return _response(cart, list(items))


@router.patch(
    "/items/{item_id}",
    response_model=ShoppingCartResponse,
    summary="Replace an owned cart item quantity",
)
async def update_cart_item(
    item_id: UUID,
    payload: CartItemQuantityUpdate,
    request: Request,
    actor: CustomerActor,
    service: CartApplication,
) -> ShoppingCartResponse:
    cart, items = await service.update_item(
        actor.principal.subject, item_id, payload.quantity, _request_id(request)
    )
    return _response(cart, list(items))


@router.delete(
    "/items/{item_id}",
    response_model=ShoppingCartResponse,
    summary="Remove an owned cart item",
)
async def remove_cart_item(
    item_id: UUID,
    request: Request,
    actor: CustomerActor,
    service: CartApplication,
) -> ShoppingCartResponse:
    cart, items = await service.remove_item(actor.principal.subject, item_id, _request_id(request))
    return _response(cart, list(items))


@router.delete(
    "/items",
    response_model=ShoppingCartResponse,
    summary="Clear all items from the current cart",
)
async def clear_cart(
    request: Request,
    actor: CustomerActor,
    service: CartApplication,
) -> ShoppingCartResponse:
    cart, items = await service.clear(actor.principal.subject, _request_id(request))
    return _response(cart, list(items))
