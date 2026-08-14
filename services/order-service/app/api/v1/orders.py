"""Authenticated checkout, order history, and controlled lifecycle routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.api.dependencies import (
    get_authenticated_actor,
    get_checkout_service,
    get_customer_actor,
    get_order_service,
)
from app.application.checkout import CheckoutService
from app.application.orders import OrderService
from app.core.security import AuthenticatedActor
from app.domain.models import Order, OrderAuditEvent, OrderItem, OrderStatus, OrderStatusHistory
from app.schemas.order import (
    AdministrativeStatusTransition,
    OrderAuditEventResponse,
    OrderAuditPageResponse,
    OrderConfirmationResponse,
    OrderHistoryResponse,
    OrderItemResponse,
    OrderPageResponse,
    OrderStatusHistoryResponse,
    OrderSummaryResponse,
)

router = APIRouter(prefix="/orders", tags=["Order checkout"])
CustomerActor = Annotated[AuthenticatedActor, Depends(get_customer_actor)]
Authenticated = Annotated[AuthenticatedActor, Depends(get_authenticated_actor)]
CheckoutApplication = Annotated[CheckoutService, Depends(get_checkout_service)]
OrderApplication = Annotated[OrderService, Depends(get_order_service)]
StatusFilter = Annotated[OrderStatus | None, Query(alias="status")]
PageOffset = Annotated[int, Query(ge=0)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
CustomerSubjectFilter = Annotated[str | None, Query(min_length=1, max_length=255)]
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


def _summary(order: Order) -> OrderSummaryResponse:
    return OrderSummaryResponse(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status.value,
        currency_code=order.currency_code,
        total=order.total,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _history_response(
    order: Order, entries: list[OrderStatusHistory], *, administrative: bool
) -> OrderHistoryResponse:
    return OrderHistoryResponse(
        order_id=order.id,
        current_status=order.status.value,
        items=[
            OrderStatusHistoryResponse(
                status=entry.status.value,
                actor_subject=(
                    entry.actor_subject
                    if administrative
                    else (
                        "customer:self"
                        if entry.actor_subject == order.customer_identity_subject
                        else "platform_actor"
                    )
                ),
                correlation_id=entry.correlation_id,
                occurred_at=entry.occurred_at,
            )
            for entry in entries
        ],
    )


def _audit_response(
    order: Order,
    entries: list[OrderAuditEvent],
    offset: int,
    limit: int,
    total: int,
    *,
    administrative: bool,
) -> OrderAuditPageResponse:
    return OrderAuditPageResponse(
        order_id=order.id,
        items=[
            OrderAuditEventResponse(
                action=entry.action,
                actor_subject=(
                    entry.actor_subject
                    if administrative
                    else (
                        "customer:self"
                        if entry.actor_subject == order.customer_identity_subject
                        else "platform_actor"
                    )
                ),
                correlation_id=entry.correlation_id,
                contextual_information=entry.metadata,
                occurred_at=entry.occurred_at,
            )
            for entry in entries
        ],
        offset=offset,
        limit=limit,
        total=total,
    )


@router.post(
    "/checkout",
    response_model=OrderConfirmationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout the authenticated customer's active cart",
)
async def checkout(
    request: Request,
    idempotency_key: IdempotencyKey,
    actor: CustomerActor,
    service: CheckoutApplication,
) -> OrderConfirmationResponse:
    request.app.state.metrics.checkout_started()
    try:
        order, items = await service.checkout(
            actor.principal.subject,
            actor.access_token,
            idempotency_key,
            str(request.state.correlation_id),
        )
    except Exception:
        request.app.state.metrics.observe_checkout("failure")
        raise
    request.app.state.metrics.observe_checkout("success")
    return _response(order, list(items))


@router.get("/me", response_model=OrderPageResponse)
async def list_my_orders(
    actor: CustomerActor,
    service: OrderApplication,
    order_status: StatusFilter = None,
    offset: PageOffset = 0,
    limit: PageLimit = 25,
    sort: Literal["created_at_desc", "created_at_asc"] = "created_at_desc",
) -> OrderPageResponse:
    orders, total = await service.list_orders(
        actor.principal,
        customer_subject=None,
        status=order_status,
        offset=offset,
        limit=limit,
        ascending=sort == "created_at_asc",
        administrative=False,
    )
    return OrderPageResponse(
        items=[_summary(order) for order in orders], offset=offset, limit=limit, total=total
    )


@router.get("/me/{order_id}", response_model=OrderConfirmationResponse)
async def get_my_order(
    order_id: UUID, actor: CustomerActor, service: OrderApplication
) -> OrderConfirmationResponse:
    order, items = await service.detail(actor.principal, order_id, administrative=False)
    return _response(order, list(items))


@router.get("/me/{order_id}/history", response_model=OrderHistoryResponse)
async def get_my_order_history(
    order_id: UUID, actor: CustomerActor, service: OrderApplication
) -> OrderHistoryResponse:
    order, entries = await service.history(actor.principal, order_id, administrative=False)
    return _history_response(order, list(entries), administrative=False)


@router.get("/me/{order_id}/audit", response_model=OrderAuditPageResponse)
async def get_my_order_audit(
    order_id: UUID,
    actor: CustomerActor,
    service: OrderApplication,
    offset: PageOffset = 0,
    limit: PageLimit = 25,
) -> OrderAuditPageResponse:
    order, entries, total = await service.audit(
        actor.principal, order_id, offset=offset, limit=limit, administrative=False
    )
    return _audit_response(order, list(entries), offset, limit, total, administrative=False)


@router.post("/me/{order_id}/cancellation", response_model=OrderSummaryResponse)
async def cancel_my_order(
    order_id: UUID, request: Request, actor: CustomerActor, service: OrderApplication
) -> OrderSummaryResponse:
    try:
        order = await service.cancel(
            actor.principal,
            order_id,
            str(request.state.correlation_id),
            administrative=False,
        )
    except Exception:
        request.app.state.metrics.observe_transition("CANCELLED", "failure")
        raise
    request.app.state.metrics.observe_transition("CANCELLED", "success")
    return _summary(order)


@router.get("/admin", response_model=OrderPageResponse)
async def list_operational_orders(
    actor: Authenticated,
    service: OrderApplication,
    customer_subject: CustomerSubjectFilter = None,
    order_status: StatusFilter = None,
    offset: PageOffset = 0,
    limit: PageLimit = 25,
    sort: Literal["created_at_desc", "created_at_asc"] = "created_at_desc",
) -> OrderPageResponse:
    orders, total = await service.list_orders(
        actor.principal,
        customer_subject=customer_subject,
        status=order_status,
        offset=offset,
        limit=limit,
        ascending=sort == "created_at_asc",
        administrative=True,
    )
    return OrderPageResponse(
        items=[_summary(order) for order in orders], offset=offset, limit=limit, total=total
    )


@router.get("/admin/{order_id}", response_model=OrderConfirmationResponse)
async def get_operational_order(
    order_id: UUID, actor: Authenticated, service: OrderApplication
) -> OrderConfirmationResponse:
    order, items = await service.detail(actor.principal, order_id, administrative=True)
    return _response(order, list(items))


@router.get("/admin/{order_id}/history", response_model=OrderHistoryResponse)
async def get_operational_order_history(
    order_id: UUID, actor: Authenticated, service: OrderApplication
) -> OrderHistoryResponse:
    order, entries = await service.history(actor.principal, order_id, administrative=True)
    return _history_response(order, list(entries), administrative=True)


@router.get("/admin/{order_id}/audit", response_model=OrderAuditPageResponse)
async def get_operational_order_audit(
    order_id: UUID,
    actor: Authenticated,
    service: OrderApplication,
    offset: PageOffset = 0,
    limit: PageLimit = 25,
) -> OrderAuditPageResponse:
    order, entries, total = await service.audit(
        actor.principal, order_id, offset=offset, limit=limit, administrative=True
    )
    return _audit_response(order, list(entries), offset, limit, total, administrative=True)


@router.post("/admin/{order_id}/status", response_model=OrderSummaryResponse)
async def transition_order_status(
    order_id: UUID,
    payload: AdministrativeStatusTransition,
    request: Request,
    actor: Authenticated,
    service: OrderApplication,
) -> OrderSummaryResponse:
    target = OrderStatus(payload.target_status)
    try:
        order = await service.transition(
            actor.principal,
            order_id,
            target,
            str(request.state.correlation_id),
        )
    except Exception:
        request.app.state.metrics.observe_transition(target.value, "failure")
        raise
    request.app.state.metrics.observe_transition(target.value, "success")
    return _summary(order)


@router.post("/admin/{order_id}/cancellation", response_model=OrderSummaryResponse)
async def cancel_operational_order(
    order_id: UUID,
    request: Request,
    actor: Authenticated,
    service: OrderApplication,
) -> OrderSummaryResponse:
    try:
        order = await service.cancel(
            actor.principal,
            order_id,
            str(request.state.correlation_id),
            administrative=True,
        )
    except Exception:
        request.app.state.metrics.observe_transition("CANCELLED", "failure")
        raise
    request.app.state.metrics.observe_transition("CANCELLED", "success")
    return _summary(order)
