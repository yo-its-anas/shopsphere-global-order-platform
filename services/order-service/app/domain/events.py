"""Versioned, non-sensitive order event contracts."""

from app.domain.models import Order, OrderDomainEvent

ORDER_CREATED = "order.created.v1"
ORDER_CONFIRMED = "order.confirmed.v1"
ORDER_STATUS_CHANGED = "order.status_changed.v1"
ORDER_CANCELLED = "order.cancelled.v1"


def order_created(order: Order, item_count: int, correlation_id: str) -> OrderDomainEvent:
    return OrderDomainEvent(
        event_type=ORDER_CREATED,
        aggregate_id=order.id,
        correlation_id=correlation_id,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status.value,
            "currency_code": order.currency_code,
            "total": format(order.total, "f"),
            "item_count": item_count,
        },
    )


def order_confirmed(order: Order, correlation_id: str) -> OrderDomainEvent:
    return OrderDomainEvent(
        event_type=ORDER_CONFIRMED,
        aggregate_id=order.id,
        correlation_id=correlation_id,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status.value,
            "currency_code": order.currency_code,
            "total": format(order.total, "f"),
        },
    )


def order_status_changed(
    order: Order, previous_status: str, correlation_id: str
) -> OrderDomainEvent:
    return OrderDomainEvent(
        event_type=ORDER_STATUS_CHANGED,
        aggregate_id=order.id,
        correlation_id=correlation_id,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "previous_status": previous_status,
            "status": order.status.value,
        },
    )


def order_cancelled(order: Order, correlation_id: str) -> OrderDomainEvent:
    return OrderDomainEvent(
        event_type=ORDER_CANCELLED,
        aggregate_id=order.id,
        correlation_id=correlation_id,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status.value,
        },
    )
