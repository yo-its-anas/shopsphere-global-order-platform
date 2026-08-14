# Order Processing Administration Guide

This guide describes governed PoC order operations. It does not grant database editing,
refund processing, shipment tracking or unrestricted status mutation.

## Roles and screens

- `support` may open `/order-management` and view governed order detail, status history
  and safe transaction audit. Support cannot change status or cancel an order.
- `operations_admin` may use the same operational views and only the explicit transitions
  permitted by the backend state machine: `CONFIRMED → PROCESSING → FULFILLED`, plus
  eligible cancellation from CONFIRMED or PROCESSING.
- Customers manage only their own cart and orders. No operational role implicitly
  impersonates a customer cart.

Rejected arbitrary or invalid transitions are expected security/domain behavior. Never
edit `orders`, `order_items`, `order_status_history` or `order_audit_events` directly.
Historical items, status history and audit rows are append-only evidence.

## Operational checks

```bash
make postgresql-status
make keycloak-status
make catalogue-service-status
make order-service-status
make api-gateway-status
make kafka-status
make redis-status
```

PostgreSQL is critical for order readiness. Catalogue availability is required for cart
validation and checkout but not for persisted order-history reads. Kafka failure leaves
pending outbox rows for retry and must not invalidate a committed order. Redis is a
Catalogue performance optimization; authoritative operations fall back to PostgreSQL.

Use `make order-service-smoke` for the controlled deployed smoke test. Use
`make order-e2e PYTHON=services/order-service/.venv/bin/python` only against the dedicated
PoC: it deliberately performs bounded Kafka and Redis outage/recovery scenarios with
simulated data. Verify both workloads afterward. The runner retains append-only synthetic
orders as evidence and removes temporary Keycloak clients.

## Reconciliation and security limitations

Failed compensation is retained in `checkout_attempts.unresolved_reservations`; the PoC
does not include a durable automatic reconciliation/expiry worker. Operators must not
delete this evidence. Never print tokens, service-client secrets, database URLs or
Kubernetes Secret values while investigating.

The single VM, kind node, PostgreSQL server, Redis instance and Kafka broker provide no
infrastructure-level HA. Production requires monitored durable reconciliation workers,
managed HA data services, multi-zone GKE, resilient consumers and tested disaster
recovery.
