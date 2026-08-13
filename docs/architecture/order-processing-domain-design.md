# Enterprise Order Processing Domain Design

## Status and evidence boundary

This document describes the implemented Enterprise Order Processing bounded context and
its validated PoC boundaries. Repository evidence includes four Alembic revisions,
customer-owned cart and order APIs, Catalogue inventory reservations, fixed API Gateway
routes, React order screens, Kubernetes deployment, transactional outbox publication,
46 passing order-service tests and the passing API-driven E2E scenarios recorded in
`docs/evidence/order-processing-e2e-evidence.md`. The E2E runner used simulated data and
did not automate a browser.

The design is governed by [ADR-001](../adr/ADR-001-modular-microservices-architecture.md),
[ADR-004](../adr/ADR-004-fastapi-versioned-rest-apis.md),
[ADR-005](../adr/ADR-005-keycloak-identity-rbac.md),
[ADR-006](../adr/ADR-006-postgresql-redis-data-platform.md),
[ADR-007](../adr/ADR-007-kafka-domain-events.md),
[ADR-010](../adr/ADR-010-utc-timestamps-json-logs.md), and
[ADR-011](../adr/ADR-011-reservation-based-order-saga.md).

## Bounded context and ownership

`order-service` is the sole owner of:

- customer carts and cart items;
- orders and immutable order-item commercial snapshots;
- order lifecycle and append-only status history;
- order transaction audit records;
- checkout idempotency and Saga progress; and
- order-domain outbox records and events.

`catalogue-service` remains authoritative for products, sellable lifecycle state,
effective prices, inventory balances, availability, reservations, releases, and future
fulfilment consumption. `customer-service` remains authoritative for customer business
profiles. Keycloak remains authoritative for identity, credentials, tokens, and roles.

No service may read or modify another service's tables. Sharing one PostgreSQL server in
the PoC does not weaken this rule. Cross-context work uses authenticated, versioned APIs
and asynchronous facts.

```mermaid
flowchart LR
    UI[React client] -->|Bearer token and Idempotency-Key| GW[API Gateway]
    GW -->|fixed /api/v1 order routes| ORD[order-service]
    ORD --> ODB[(order-owned PostgreSQL tables)]
    ORD -->|service-authenticated quote and reserve command| CAT[catalogue-service]
    CAT --> CDB[(catalogue and inventory tables)]
    ORD -->|order outbox relay| K[Kafka]
    CAT -->|inventory outbox relay| K
    ORD -.->|validated customer reference when needed| CUST[customer-service]
    KC[Keycloak] -.->|JWKS and governed roles| ORD
```

The browser may request cart changes and checkout but is never authoritative for price,
totals, product validity, availability, ownership, or status transitions.

## Implemented entity model

All domain identifiers are UUIDs. Stored instants are timezone-aware UTC. Human-readable
numbers and external references are alternate keys, not database primary keys.

### ShoppingCart

The ShoppingCart aggregate represents a customer's mutable purchase intent:

- `id`: immutable UUID;
- `customer_identity_subject`: immutable Keycloak `sub` used for ownership checks;
- `status`: `ACTIVE` or `CHECKED_OUT`;
- `currency_code`: one ISO 4217 currency for the cart;
- `version`: optimistic concurrency token; and
- `created_at` and `updated_at` UTC timestamps.

The PoC allows one active cart per customer and currency through a partial unique index.
Checkout records the claimed cart version in `CheckoutAttempt`; successful checkout marks
the cart `CHECKED_OUT`, while a known failed checkout leaves it active. Cart display prices
may be refreshed from Catalogue, but they are estimates and are never checkout authority.

### CartItem

A CartItem belongs to exactly one cart and contains:

- `id`, `cart_id`, and authoritative Catalogue `product_id` UUIDs;
- a positive integer `quantity` with a governed upper bound;
- last-seen SKU, name, price, currency and availability display data treated as non-binding; and
- UTC creation/update timestamps.

The `(cart_id, product_id)` pair is unique so adding the same product changes quantity
rather than creating ambiguous duplicate lines. Product references are validated through
Catalogue at a bounded point; final sellability, price, currency, and availability are
always revalidated at checkout.

### Order

Order is the lifecycle and consistency aggregate:

- `id`: immutable UUID;
- `order_number`: unique opaque customer-facing reference;
- `customer_identity_subject` ownership reference;
- source `cart_id`;
- lifecycle `status`; separate `CheckoutAttempt` records hold Saga state;
- `currency_code`;
- exact `subtotal` and `total` values; and
- `created_at` and `updated_at` UTC timestamps.

Discount, taxation, payment processing and card data are outside this implemented
bounded context; the confirmation explicitly reports payment as not in scope.

### OrderItem

OrderItem is an immutable commercial snapshot created only after authoritative Catalogue
product/price reads and a successful inventory reservation. It stores:

- `id`, `order_id`, and source `product_id`;
- SKU and product name at checkout;
- purchased quantity;
- exact unit price and ISO currency;
- exact line total; and
- UTC creation time.

Historical order display reads this snapshot, not live Catalogue metadata or pricing.
Clients cannot submit accepted prices or totals. A later Catalogue rename, price change,
deactivation, or deletion policy cannot rewrite an existing OrderItem.

### OrderStatusHistory

OrderStatusHistory is an append-only record for every accepted lifecycle transition:

- immutable UUID and `order_id`;
- resulting status;
- verified actor subject or service identity;
- correlation ID; and
- UTC occurrence time.

Update and delete must be rejected at repository and database layers. Corrections are
new compensating records, never edits to history.

### OrderAuditEvent

OrderAuditEvent is an append-only security/business accountability record. It covers
checkout initiation and outcomes, reservation acceptance or compensation, order
confirmation, cancellation and administrative transitions. It contains an immutable ID,
order ID, verified actor, action, correlation ID, UTC timestamp and allow-listed safe
metadata.

It never stores passwords, bearer or refresh tokens, Keycloak secrets, unrestricted
request bodies, or unnecessary customer personal data. Operational JSON logs remain
diagnostic telemetry and are not a substitute for this audit ledger.

### OrderOutboxEvent

OrderOutboxEvent records event intent in the same PostgreSQL transaction as the order
change. It follows the existing versioned envelope: `event_id`, `event_type`,
`event_version`, `aggregate_type`, `aggregate_id`, `occurred_at`, `correlation_id`,
`producer`, and a minimal payload. Relay state includes attempts, next availability,
publication time, and a safe error category.

Delivery is at least once. Consumers must deduplicate by `event_id`; a published flag is
relay state, not proof that every consumer processed the event.

## Aggregate and monetary invariants

1. A cart and its items belong to one verified Keycloak subject; ownership never comes
   from a path parameter or browser-supplied customer identifier.
2. Only an `ACTIVE` cart can change or enter checkout. The durable CheckoutAttempt stores
   the claimed cart version; a `CHECKED_OUT` cart is immutable.
3. Item quantity is a positive bounded integer and `(cart_id, product_id)` is unique.
4. An OrderItem snapshot is immutable after confirmation and originates only from an
   authoritative Catalogue response.
5. One order has one currency. Mixed-currency checkout is rejected rather than silently
   converted.
6. Money uses Python `Decimal` and PostgreSQL `NUMERIC(19,4)`, never binary floating
   point. Currency-specific display rounding is presentation policy.
7. `line_total = unit_price * quantity`; `subtotal = sum(line_total)`; and in the current
   scope `total = subtotal`. All amounts are non-negative and recalculated server-side.
8. Every accepted status change appends OrderStatusHistory and OrderAuditEvent records
   in the same order database transaction.
9. Order snapshots, history, audit, and outbox rows are never physically deleted through
   ordinary business APIs.
10. A successful checkout idempotency scope produces at most one order.

## Order lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING: checkout accepted
    PENDING --> CONFIRMED: authoritative quote and reservation accepted
    PENDING --> FAILED: known unrecoverable checkout failure
    CONFIRMED --> PROCESSING: controlled operational action
    CONFIRMED --> CANCELLED: cancel and release reservation
    PROCESSING --> FULFILLED: inventory consumption accepted
    PROCESSING --> CANCELLED: explicitly permitted cancel and release
    CANCELLED --> [*]
    FULFILLED --> [*]
    FAILED --> [*]
```

The implemented PoC represents the pre-order `PENDING` portion as a durable
`CheckoutAttempt(PROCESSING)` Saga record. It materializes the `Order` aggregate only
after authoritative quote and reservation acceptance, directly in `CONFIRMED`. `PENDING`
and `FAILED` remain recognized internal lifecycle concepts, but no public command can set
them. This avoids presenting an unconfirmed record as a customer order while preserving
retry and reconciliation evidence.

`FAILED` is retained as an internal terminal state for a checkout/order record whose
failure is known and compensated. An uncertain remote outcome remains `PENDING` for
reconciliation; it must not be guessed as failed. `FULFILLED`, `CANCELLED`, and `FAILED`
are terminal in the PoC. Direct transitions such as `PENDING` to `FULFILLED`, reopening a
cancelled order, or editing a fulfilled snapshot are rejected.

Cancellation is allowed only while Inventory can authoritatively release an unconsumed
reservation. Fulfilment is recorded only after Inventory atomically consumes each
reservation by reducing both on-hand and reserved quantities. These fixed-origin commands
and their idempotent order-service orchestration are implemented and unit validated.
The E2E cancellation scenario exercised release through the deployed service identity;
the PROCESSING-to-FULFILLED consumption path is unit validated but not separately E2E
validated.

## Reservation-based checkout Saga

The preferred PoC orchestration is an order-service-owned Saga with synchronous command
results for correctness and asynchronous events for downstream facts.

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant UI as React
    participant GW as API Gateway
    participant ORD as order-service
    participant ODB as order_db
    participant CAT as catalogue-service
    participant CDB as catalogue_db
    participant K as Kafka

    Customer->>UI: Checkout active cart
    UI->>GW: POST /api/v1/orders/checkout<br/>Bearer + Idempotency-Key
    GW->>ORD: Fixed-route forwarding + correlation ID
    ORD->>ORD: Validate JWT, role, cart ownership and request
    ORD->>ODB: Claim customer-scoped key and persist PROCESSING attempt
    loop Each cart line
        ORD->>CAT: Read authoritative product and current price
        ORD->>CAT: Reserve quantity using service identity<br/>and stable external reference
        CAT->>CDB: Lock inventory row, validate availability,<br/>persist ACTIVE reservation/movement/outbox
        CAT-->>ORD: Reservation receipt
    end
    ORD->>ORD: Calculate Decimal lines and total
    ORD->>ODB: Atomically persist CONFIRMED order, immutable items,<br/>history, audit, checked-out cart, idempotent result and outbox
    ORD-->>UI: Order confirmation and stable order reference
    ODB-->>K: Asynchronous order outbox relay
    CDB-->>K: Asynchronous inventory outbox relay
```

Catalogue now implements a single-product reservation record plus idempotent
reserve/retrieve/release/consume commands. Each mutation locks its InventoryItem and
commits the balance, reservation, movement, and outbox intent atomically. Order-service
reserves multi-line carts sequentially. If a later line fails, it releases earlier ACTIVE
reservations; an unresolved release is retained in `checkout_attempts` as reconciliation
evidence. Automatic reservation expiry and a durable reconciliation worker are not
implemented.

## Idempotency and replay handling

Checkout requires an opaque `Idempotency-Key` with a bounded length. Order-service stores
a unique scope such as `(customer_identity_subject, operation, key)`, a canonical request
fingerprint, processing state, and the resulting order reference/response metadata.

- The first request atomically claims the key before remote work.
- The same key and fingerprint returns the original result or current processing status;
  it never creates another order.
- Reusing the key with a different cart/version or payload returns `409 Conflict`.
- A concurrent duplicate loses the unique-key race and reads the winning record.
- Catalogue reservation, release, and fulfilment commands use stable derived idempotency
  keys so a retry cannot double-reserve or double-release.
- Keys must not contain customer data or credentials and are retained longer than
  expected client/network retries under a governed retention policy.

Cart version is included in the checkout fingerprint. A stale client cannot check out a
different cart state under the same key.

## Concurrency and failure handling

| Condition | Required behavior |
| --- | --- |
| Two customers request the final unit | Catalogue locks InventoryItem rows and evaluates current available stock inside one transaction. Only one reservation commits; the other receives a stable availability conflict. |
| Duplicate checkout requests | Order idempotency returns the same result. Catalogue command idempotency prevents duplicate reservation. |
| Network timeout after reservation | Retry/query by the same reservation idempotency key. Keep the CheckoutAttempt `PROCESSING` until the authoritative result is known. |
| Network timeout after order commit | A retry with the same checkout key returns the committed confirmation. |
| Catalogue unavailable before reservation | Return a bounded retryable response, preserve the active cart, and do not confirm an order. |
| Catalogue fails during one reservation | That line's PostgreSQL transaction rolls back; order-service releases any earlier line reservations and records unresolved compensation if release fails. |
| Order database fails before reservation | No remote inventory change is attempted. |
| Order database fails after reservation | Invoke idempotent release; if release fails, retain the reservation ID in `checkout_attempts.unresolved_reservations`. The PoC has no automatic reconciler. |
| Reservations succeed but final order commit fails | Attempt release for every reservation and retain unresolved evidence. Never create a second order for the same customer/idempotency key. |
| Cancellation release is unavailable | Do not report cancellation complete while stock remains reserved; retain retryable workflow state. |
| Kafka unavailable | Database commits retain pending outbox rows. Relays retry; checkout correctness never depends on Kafka availability. |
| Unknown remote outcome | Reconcile by stable command/reservation ID; never infer success or failure from timeout alone. |

The implemented reservation states are `ACTIVE`, `RELEASED`, and `CONSUMED`; an optional
expiry timestamp is stored for future use, but no expiry worker or `EXPIRED` transition is
implemented. Production requires an idempotent, auditable expiry and reconciliation
mechanism that cannot silently expire inventory beneath a confirmed order.

## Authorization model

Keycloak authenticates actors and supplies governed roles. API Gateway forwarding and
frontend navigation are not authoritative; order-service validates signature, issuer,
audience, expiry, and roles and performs resource-level ownership checks.

| Actor | Cart access | Order access | Lifecycle commands |
| --- | --- | --- | --- |
| `customer` | Create/read/change only the active cart mapped to verified `sub`; check out only that cart | List/read only orders mapped to verified `sub` | May request an explicitly permitted cancellation of an eligible own order; cannot set status directly |
| `support` | No customer cart mutation | Read customer orders/history for justified support purposes | No unrestricted transition or commercial-data modification rights |
| `operations_admin` | No ordinary impersonated cart mutation | Governed operational search/read | Only explicit commands allowed by the state machine, with reason and audit; cannot rewrite snapshots or history |
| order-service identity | No user-facing cart authority | Own persistence only | Invoke Catalogue reservation/retrieve/release/consume contracts through the deployed least-privilege `order_service` role |

Administrative routes must express commands such as `start-processing`, `fulfil`, or
`cancel`, not expose a generic writable `status` field. Support and administrator reads
must be paginated, purpose-limited, safely logged, and audited where appropriate.

## Security and threat treatment

| Threat | Design control |
| --- | --- |
| IDOR and cross-customer access | Resolve ownership from validated `sub` for every cart/order/item; never accept customer identity from URL/body as authorization evidence. |
| Browser-manipulated prices/totals | Ignore or reject client commercial amounts. Obtain the snapshot from Catalogue and recalculate with Decimal. |
| Manipulated product IDs/quantities | Validate UUIDs and bounded positive quantities; Catalogue verifies lifecycle, currency, price, and availability. |
| Duplicate/replayed checkout | Actor-scoped idempotency, request fingerprint, cart version, reservation idempotency, and safe conflict behavior. |
| Excessive administrative privilege | Deny by default, explicit transition commands, least privilege, reason requirements, negative tests, and audit. |
| JWT abuse | Validate signature, issuer, audience, algorithm, expiry, and claims; never log tokens; require TLS in production. |
| Audit data exposure | Separate authorization, minimal metadata, append-only storage, retention controls, pagination, and no secrets or unnecessary PII. |

Order confirmation is a server-generated representation of the committed immutable
snapshot and stable order reference. It is not proof of payment. Email delivery may be a
later notification concern and must consume order facts rather than own order state.

## Implemented domain events

- `order.created.v1` — durable order identity and immutable commercial snapshot exist;
- `order.confirmed.v1` — authoritative inventory reservation was accepted;
- `order.status_changed.v1` — an allowed lifecycle transition committed; and
- `order.cancelled.v1` — cancellation and required inventory compensation completed.

Payloads contain opaque references, status, currency, exact amount strings, correlation
identifiers, and only governed consumer data. They exclude JWTs,
credentials, payment data, and unnecessary PII. Per-order events use the order UUID as
the Kafka key to preserve partition order where possible. Global ordering is not
promised. All four contracts, their transactional outbox records, PostgreSQL lease/retry
store and the same configurable at-least-once relay used by Catalogue are implemented.
An acknowledgement failure after Kafka accepts a message can publish the same `event_id`
again; consumers must deduplicate that stable identifier. Structured publish/defer/poll
logs provide operational visibility without payloads or credentials. The E2E Kafka
failure scenario proved that a CONFIRMED order retained pending outbox rows and that the
expected events published after Kafka was restored.

## API shape

The following cart routes are implemented internally in order-service:

- `GET /api/v1/carts/me` — create if absent and retrieve the actor's active cart;
- `POST /api/v1/carts/me/items` — validate a product and add/increment an item;
- `PATCH /api/v1/carts/me/items/{item_id}` — replace an owned item quantity;
- `DELETE /api/v1/carts/me/items/{item_id}` — remove an owned item; and
- `DELETE /api/v1/carts/me/items` — clear the owned cart.

Their Catalogue price/availability fields and subtotal are display snapshots, not checkout
authority. The Gateway exposes the implemented checkout route:

- `POST /api/v1/orders/checkout` — customer-owned checkout requiring `Idempotency-Key`.

Actor-scoped routes are implemented under `/api/v1/orders/me` for customer list,
detail, history, audit and cancellation. Operational routes are implemented under
`/api/v1/orders/admin` for support/admin list, detail, history and audit. Only
`operations_admin` can invoke the explicit status and administrative cancellation
commands. API Gateway exposes an explicit allow-list for these paths and rejects arbitrary
order subpaths.

Order-service-to-Catalogue reservation endpoints are internal fixed destinations, not
arbitrary proxy URLs and not ordinary browser routes. They require a least-privilege
service identity and correlation/causation propagation.

## PoC trade-offs and implementation boundary

The PoC packages Saga orchestration and outbox relay with one order-service process.
A separate logical `order_db`, owned by least-privilege `order_app`, is provisioned
on the existing PostgreSQL server. It improves ownership hygiene but provides no
infrastructure isolation, independent scaling, or high availability. Four cart/order/
outbox migrations are applied and platform validated. Checkout, history, RBAC, lifecycle,
cancellation, reservation/release orchestration, audit and event publication are unit
validated; the retained API-driven E2E report validates scenarios A–I with simulated data.

The current single PostgreSQL instance, single Redis instance, single Kafka broker,
single kind node, and single physical GCP VM form one failure domain. Redis is not
required for initial order correctness and should not cache authoritative order state or
idempotency results. Kafka is asynchronous transport, not the checkout transaction
coordinator. Multiple pods on the single node would not provide host-level HA.

The PoC favours synchronous authoritative reads followed by sequential reservations for
a deterministic demonstration, a database-backed Saga/outbox for recovery, one currency
per order, one inventory location, and no payment/tax/promotion implementation.
Reservation expiry and durable reconciliation are required before calling checkout
production-ready.

## Production evolution

- Use an independently managed, regional/HA order database with encrypted automated
  backups, PITR, tested failover, connection pooling, partitioned/archived audit and
  history, and explicit recovery objectives.
- Run a horizontally scalable stateless order-service on multi-zone GKE behind managed
  load balancing, with workload identity, mTLS/private connectivity, external secret
  management, enforced network policy, disruption budgets, autoscaling, rate limits,
  and SLO-driven telemetry.
- Adopt a durable workflow engine or rigorously operated Saga/reconciliation workers for
  long-running reservation, cancellation, fulfilment, and later payment processes.
- Use managed or multi-broker Kafka with replication, TLS, ACLs, schema governance,
  monitored outbox/consumer lag, dead-letter strategy, and idempotent consumers.
- Use replicated/managed Redis only for disposable projections and introduce a deliberate
  multi-region strategy where latency, recovery objectives and data residency require it.
- Operate resilient event consumers, durable reconciliation workers and tested database,
  event and configuration disaster-recovery procedures.
- Scale Inventory independently when contention warrants it; retain deterministic locks,
  reservation leases, command idempotency, reconciliation, and oversell monitoring.
- Add governed tax, discount, payment, fraud, fulfilment, notification, privacy, and
  retention capabilities only with explicit ownership.

## Architecture defence notes

- A cart is intent; an order is an immutable historical commercial record.
- Catalogue supplies the authoritative commercial snapshot and Inventory owns stock.
- A synchronous reservation result prevents overselling; events distribute facts after
  commit and cannot authorize checkout.
- A Saga avoids an unsafe distributed transaction and makes compensation explicit.
- Idempotency protects both the customer experience and inventory from retries.
- Decimal snapshots preserve history even when catalogue names or prices change.
- RBAC grants capabilities, while verified-subject ownership prevents IDOR.
