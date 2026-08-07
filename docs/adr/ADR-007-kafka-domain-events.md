# ADR-007: Use Kafka for asynchronous domain events

## Status

Proposed — a bootstrap-server placeholder exists, but no broker configuration, topic, schema, producer, consumer, or event test exists.

## Context

Order lifecycle changes must support decoupled analytics and future integrations without making every workflow a chain of synchronous calls. Events also demonstrate enterprise integration patterns required by the capstone.

## Decision

Use Kafka for asynchronous domain-event publication and consumption. Events use versioned schemas, stable identifiers, UTC timestamps, correlation and causation identifiers, and documented ownership. Producers use a transactional outbox where reliable database-to-event publication is required; consumers must be idempotent.

## Alternatives considered

- Synchronous REST only: simpler but couples availability and limits event-driven analytics.
- RabbitMQ: strong task and routing semantics, but Kafka better supports durable event streams and replay-oriented analytics.
- Redis Pub/Sub: operationally convenient but lacks the durability and replay guarantees required for domain events.

## Consequences

Consumers can evolve independently and replay governed event streams. Kafka adds operational overhead, eventual consistency, schema compatibility, ordering, retry, duplicate handling, and observability requirements.

## Security implications

Restrict topic access per workload, encrypt transport, authenticate clients, protect payloads from unnecessary personal data, validate schemas, audit administrative operations, and govern retention and deletion obligations.

## PoC limitations

A single broker on one VM cannot demonstrate broker redundancy or production throughput. Failure recovery and schema governance will be limited. Kafka is not currently deployed.

## Production evolution

Use a managed or multi-broker multi-zone Kafka platform, replicated topics, formal schema registry, quotas, dead-letter and retry policies, disaster recovery, capacity planning, and monitored consumer lag.

## Viva defence notes

Explain that Kafka complements rather than replaces REST: commands and immediate queries can remain synchronous, while durable facts such as order state changes are published asynchronously. Discuss idempotency and eventual consistency explicitly.
