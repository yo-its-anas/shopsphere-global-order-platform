"""Authenticated order checkout routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.api.dependencies import get_checkout_service, get_customer_actor
from app.application.checkout import CheckoutService
from app.core.security import AuthenticatedActor
from app.domain.models import Order, OrderItem
from app.schemas.order import OrderConfirmationResponse, OrderItemResponse

router = APIRouter(prefix="/orders", tags=["Order checkout"])
CustomerActor = Annotated[AuthenticatedActor, Depends(get_customer_actor)]
CheckoutApplication = Annotated[CheckoutService, Depends(get_checkout_service)]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        description="Customer-scoped retry key; reuse only for the same checkout intent.",
    ),
]


def _response(order: Order, items: list[OrderItem]) -> OrderConfirmationResponse:
    return OrderConfirmationResponse(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status.value,
        items=[
            OrderItemResponse(
                product_id=item.product_id,
                sku=item.sku,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency_code=item.currency_code,
                line_total=item.line_total,
            )
            for item in items
        ],
        currency_code=order.currency_code,
        subtotal=order.subtotal,
        total=order.total,
        created_at=order.created_at,
    )


@router.post(
    "/checkout",
    response_model=OrderConfirmationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout the authenticated customer's active cart",
    description=(
        "Revalidates authoritative catalogue pricing and reserves inventory before "
        "atomically recording a confirmed order. Payment processing is out of scope."
    ),
)
async def checkout(
    request: Request,
    idempotency_key: IdempotencyKey,
    actor: CustomerActor,
    service: CheckoutApplication,
) -> OrderConfirmationResponse:
    order, items = await service.checkout(
        actor.principal.subject,
        actor.access_token,
        idempotency_key,
        str(request.state.correlation_id),
    )
    return _response(order, list(items))
