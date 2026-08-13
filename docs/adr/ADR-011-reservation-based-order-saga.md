# ADR-011: Use a reservation-based Saga for order checkout

## Status

Accepted and implemented for the PoC.

## Context

Checkout spans order-owned carts and orders plus Catalogue-owned product, price, and
inventory state. Concurrent customers may request the final unit, clients may retry
after timeouts, and either service or Kafka may be temporarily unavailable. A direct
cross-service database transaction would violate ownership and cannot be made reliable
as an ordinary PostgreSQL transaction across independently evolving services.

Inventory implements a single-product reservation participant with
reserve/retrieve/release/consume commands, PostgreSQL locking, idempotent external
references, movements, cache invalidation, and outbox facts. Order-service implements
customer-owned carts, idempotent checkout and Saga orchestration.

## Decision

Use an order-service-orchestrated Saga for checkout. A customer-scoped idempotency record
is claimed before remote work. Order-service obtains authoritative Catalogue data and
requests one idempotent, service-authenticated reservation per cart line. Catalogue
validates product lifecycle, effective Decimal prices, currency, and availability while
locking each inventory row. Each reservation atomically persists its balance movement
and event intent. If a later line fails, order-service releases every reservation already
obtained and retains compensation evidence.

Order-service recalculates totals and stores immutable OrderItems. It then commits
confirmation state, checked-out cart, status/audit history, idempotent result, and
OrderOutboxEvent. Release is the compensation for a hold/allocation that cannot become a
confirmed order. Hold leases and reconciliation recover crashes or unknown remote
outcomes. Kafka relays post-commit facts and never determines checkout correctness.

The full model, state machine, API direction, and failure matrix are defined in the
[Enterprise Order Processing domain design](../architecture/order-processing-domain-design.md).

## Alternatives considered

- Directly update Catalogue inventory tables from order-service: rejects service data
  ownership and creates hidden coupling.
- Distributed two-phase commit: operationally disproportionate for the PoC, tightly
  couples availability, and remains fragile across HTTP and Kafka boundaries.
- Publish a checkout event and wait for eventual reservation: decoupled, but provides a
  poor immediate checkout result and complicates oversell/user feedback for this scope.
- Check availability then create the order without reservation: contains a race and can
  oversell the final unit.
- Deduplicate only in browser or gateway: neither is an authoritative domain boundary.

## Consequences

Correctness responsibilities are explicit and each service commits only its own data.
The design handles retries and Kafka outages safely, but introduces Saga state,
compensation, reservation expiry, reconciliation, service authentication, and additional
failure-path tests. Checkout availability depends synchronously on Catalogue, while
event consumers remain eventually consistent.

## Security implications

Order-service independently validates Keycloak JWTs and resolves cart/order ownership
from verified `sub`. The internal reservation contract uses a dedicated least-privilege
confidential service client. Browser prices, totals, availability, identity fields, and
status values are untrusted. Idempotency keys are opaque and non-sensitive. Audit and
event payloads exclude tokens, credentials, payment data, and unnecessary PII.

## PoC limitations

The logical `order_db` and dedicated `order_app` identity share the PoC PostgreSQL
instance. The Catalogue reservation migration and dedicated `order_service` identity,
Order schema/Saga/outbox, fixed Gateway routes and internal Kubernetes workload are
deployed and platform-validated. A live simulated checkout/cancellation proved release
compensation and broker acknowledgement; the browser Order UI remains unimplemented.
Reservations have no automatic expiry worker, and multi-line checkout uses sequential
per-line reservations with compensation rather than an atomic multi-product hold. The
PoC still runs on one PostgreSQL instance, one Kafka broker, one kind node, and one
physical VM, with no host-level high availability. The in-process outbox publisher is
demonstrative, not a substitute for a separately operated production worker.

## Production evolution

Use independently managed HA data stores, a durable workflow engine or rigorously
operated Saga workers, reservation-expiry monitoring, multi-zone services, authenticated
and encrypted service traffic, managed multi-broker Kafka, governed schemas, mature
observability, automated reconciliation, and tested disaster recovery. Add payment,
taxation, fraud, fulfilment, and notification workflows as separately owned capabilities.

## Viva defence notes

Explain why checking availability is not reserving inventory, why retries require
idempotency at both Order and Inventory boundaries, and why a Kafka event cannot provide
the immediate authoritative reservation result. The Saga preserves service ownership
without pretending distributed work is one ACID transaction.
