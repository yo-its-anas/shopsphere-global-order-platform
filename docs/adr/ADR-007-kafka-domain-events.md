# ADR-007: Use Kafka for asynchronous domain events

## Status

Proposed — a bootstrap-server placeholder exists, but no broker configuration, topic, schema, producer, consumer, or event test exists.

## Context

Order lifecycle changes must support decoupled analytics and future integrations without making every workflow a chain of synchronous calls. Events also demonstrate enterprise integration patterns required by the capstone.

Catalogue and Inventory changes also produce useful business facts for search projections, alerts, analytics, and future Order Processing coordination. Publishing before a database commit or without retry safety could create events for state that does not exist, while publishing after commit without an outbox could lose facts.

## Decision

Use Kafka for asynchronous domain-event publication and consumption. Events use versioned schemas, stable identifiers, UTC timestamps, correlation and causation identifiers, and documented ownership. Producers use a transactional outbox where reliable database-to-event publication is required; consumers must be idempotent.

Proposed catalogue/inventory facts include `product.created`, `product.updated`, `price.changed`, `inventory.adjusted`, `inventory.low`, and `inventory.out_of_stock`. Low-stock events are emitted on a threshold transition rather than every read. Events contain the minimum non-sensitive projection and never authorize or replace the synchronous inventory transaction. A future order reservation requires an authoritative success/failure response; events distribute committed facts afterward.

## Alternatives considered

- Synchronous REST only: simpler but couples availability and limits event-driven analytics.
- RabbitMQ: strong task and routing semantics, but Kafka better supports durable event streams and replay-oriented analytics.
- Redis Pub/Sub: operationally convenient but lacks the durability and replay guarantees required for domain events.

## Consequences

Consumers can evolve independently and replay governed event streams. Kafka adds operational overhead, eventual consistency, schema compatibility, ordering, retry, duplicate handling, and observability requirements.

## Security implications

Restrict topic access per workload, encrypt transport, authenticate clients, protect payloads from unnecessary personal data, validate schemas, audit administrative operations, and govern retention and deletion obligations.

## PoC limitations

A single broker on one VM cannot demonstrate broker redundancy or production throughput. Failure recovery and schema governance will be limited. Kafka, catalogue/inventory schemas, outbox processing, producers, consumers, and these proposed events are not currently implemented.

## Production evolution

Use a managed or multi-broker multi-zone Kafka platform, replicated topics, formal schema registry, quotas, dead-letter and retry policies, disaster recovery, capacity planning, and monitored consumer lag.

## Viva defence notes

Explain that Kafka complements rather than replaces REST: commands and immediate queries can remain synchronous, while durable facts such as order state changes are published asynchronously. Discuss idempotency and eventual consistency explicitly.
