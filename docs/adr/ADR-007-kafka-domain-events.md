# ADR-007: Use Kafka for asynchronous domain events

## Status

Accepted — the PoC has a single KRaft broker, governed versioned topics, shared event
envelope conventions, Catalogue and Order PostgreSQL transactional outboxes,
asynchronous producer relays, and producer/retry/recovery evidence. No event consumers
are implemented.

## Context

Order lifecycle changes must support decoupled analytics and future integrations without making every workflow a chain of synchronous calls. Events also demonstrate enterprise integration patterns required by the capstone.

Catalogue and Inventory changes also produce useful business facts for search projections, alerts, analytics, and future Order Processing coordination. Publishing before a database commit or without retry safety could create events for state that does not exist, while publishing after commit without an outbox could lose facts.

## Decision

Use Kafka for asynchronous domain-event publication and consumption. Events use versioned schemas, stable identifiers, UTC timestamps, correlation and causation identifiers, and documented ownership. Producers use a transactional outbox where reliable database-to-event publication is required; consumers must be idempotent.

Implemented catalogue/inventory facts are `catalogue.product.created.v1`, `catalogue.product.updated.v1`, `catalogue.price.changed.v1`, `inventory.adjusted.v1`, `inventory.low.v1`, and `inventory.out-of-stock.v1`. Low/out-of-stock events are emitted on state transitions rather than every read. Events contain the minimum non-sensitive projection and never authorize or replace the synchronous inventory transaction. A future order reservation requires an authoritative success/failure response; events distribute committed facts afterward.

Order Processing publishes `order.created.v1`, `order.confirmed.v1`,
`order.status_changed.v1`, and `order.cancelled.v1` through an order-owned transactional
outbox. Checkout and reservation remain synchronous commands because an event alone
cannot provide the immediate authoritative availability decision. The E2E Kafka outage
scenario proved the committed order remained correct and pending events published after
broker restoration.

## Alternatives considered

- Synchronous REST only: simpler but couples availability and limits event-driven analytics.
- RabbitMQ: strong task and routing semantics, but Kafka better supports durable event streams and replay-oriented analytics.
- Redis Pub/Sub: operationally convenient but lacks the durability and replay guarantees required for domain events.

## Consequences

Consumers can evolve independently and replay governed event streams. Kafka adds operational overhead, eventual consistency, schema compatibility, ordering, retry, duplicate handling, and observability requirements.

## Security implications

Restrict topic access per workload, encrypt transport, authenticate clients, protect payloads from unnecessary personal data, validate schemas, audit administrative operations, and govern retention and deletion obligations.

## PoC limitations

A single combined broker/controller, one PVC, one kind node, and one VM cannot demonstrate broker redundancy, zone survival, or production throughput. The PoC internal listener is plaintext and unauthenticated, with access limited by internal Services and a declarative NetworkPolicy whose enforcement depends on the CNI. Schema-registry governance, automatic outbox archival, full broker/relay monitoring and all event consumers remain unimplemented. Producer delivery is at least once, so duplicate delivery remains possible and future consumers must deduplicate by `event_id`.

## Production evolution

Use a managed or multi-broker multi-zone Kafka platform, replication, rack/zone awareness, durable encrypted storage, TLS, workload authentication, least-privilege ACLs, formal schema governance, quotas, dead-letter and retry policies, disaster recovery, capacity planning, outbox-age monitoring, and monitored consumer lag.

## Viva defence notes

Explain that Kafka complements rather than replaces REST: commands and immediate queries can remain synchronous, while durable facts such as order state changes are published asynchronously. Discuss idempotency and eventual consistency explicitly.
