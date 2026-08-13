# ADR-011: Use a reservation-based Saga for order checkout

## Status

Accepted as the target Order Processing design — implementation is Planned.

## Context

Checkout spans order-owned carts and orders plus Catalogue-owned product, price, and
inventory state. Concurrent customers may request the final unit, clients may retry
after timeouts, and either service or Kafka may be temporarily unavailable. A direct
cross-service database transaction would violate ownership and cannot be made reliable
as an ordinary PostgreSQL transaction across independently evolving services.

Inventory now implements a unit-validated single-product reservation participant with
reserve/retrieve/release/consume commands, PostgreSQL locking, idempotent external
references, movements, cache invalidation, and outbox facts. Order-service implements
customer-owned carts but not checkout or Saga orchestration.

## Decision

Use an order-service-orchestrated Saga for checkout. A customer-scoped idempotency record
is claimed and the cart version is frozen before remote work. Order-service requests one
atomic, service-authenticated Catalogue quote-and-hold operation for all cart lines.
Catalogue validates current
product lifecycle, effective Decimal prices, currency, and availability while locking
inventory rows in deterministic order. It persists the reservation, balance movements,
and inventory event intent atomically and returns the authoritative commercial snapshot.

Order-service recalculates totals and stores immutable OrderItems while the Saga remains
pending, then idempotently allocates the hold to the durable order. It finally commits
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

The logical `order_db` and dedicated `order_app` identity are provisioned on the shared
PoC PostgreSQL instance, and cart source/migration exist. Catalogue reservation source is
unit validated, but its migration, topics, and service identity are not deployed or
platform validated. No checkout/order schema, Saga, order event producer, gateway order
route, order UI, or deployed order workload exists yet. The PoC
still runs on one PostgreSQL instance, one Kafka broker, one kind node, and one physical
VM, with no host-level high availability. A local background reconciler is
demonstrative, not a substitute for a durable production workflow platform.

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
