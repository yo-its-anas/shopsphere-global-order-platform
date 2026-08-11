# ADR-006: Use PostgreSQL for transactional data and Redis for caching

## Status

Accepted — the PoC PostgreSQL platform and customer persistence are implemented. Catalogue/inventory schemas and a catalogue-owned database remain Planned; Redis is not deployed or integrated.

## Context

Customer, catalogue, order, and reporting workflows need reliable relational persistence. Selected read paths may benefit from low-latency caching, but cached data must not become an ungoverned source of truth.

## Decision

Use PostgreSQL as the authoritative transactional datastore with SQLAlchemy and Alembic. Preserve logical ownership of service data even if the PoC consolidates database infrastructure. Use Redis only for explicitly bounded cache or ephemeral coordination use cases, with expiry and invalidation rules.

For Inventory, PostgreSQL is authoritative for `quantity_on_hand` and `quantity_reserved`; `quantity_available` is derived as their difference. Balance changes and their immutable InventoryMovement record commit in one transaction. Database constraints prevent negative on-hand/reserved balances and reservations greater than stock. Contended updates use a row lock or version-checked atomic update plus an idempotency key so concurrent requests and retries cannot silently oversell or double-apply adjustments.

For Catalogue, normalized SKU uniqueness and category keys are enforced in the database. Monetary amounts use Python `Decimal` and fixed-precision PostgreSQL `NUMERIC`, never binary floating point. Effective-dated price records retain history and prevent overlapping active ranges for the same product and ISO 4217 currency.

## Alternatives considered

- MySQL: capable, but PostgreSQL provides a strong open-source relational and extensibility baseline.
- MongoDB as the primary store: flexible documents but a weaker default fit for transactional order relationships.
- Redis as primary persistence: inappropriate for authoritative transactional records.
- No cache: simpler and remains acceptable until measured performance justifies caching.

## Consequences

Transactional integrity and migration history become explicit. Redis can improve latency but introduces invalidation, staleness, and failure-mode complexity. Services must not join across one another's owned schemas directly.

Locking protects correctness but can reduce throughput and introduce deadlocks under contention. Multi-item operations require deterministic lock ordering, bounded transaction duration, conflict handling, and observability. Search/statistics/cache projections may be eventually consistent, but availability-changing commands must use PostgreSQL authoritative state.

## Security implications

Use separate least-privilege database identities, encrypted connections, protected networks, parameterized SQL, encrypted backups, audited administrative access, and secrets outside source control. Redis must not be publicly reachable or store unnecessary sensitive data.

## PoC limitations

Single instances provide no high availability and may share host resources. Backup restoration, failover, replica behavior, and realistic cache pressure are not proven. The existing PostgreSQL initialization creates only `customer_db` and `keycloak_db`; a catalogue-owned database, credentials, schema, migrations, and persistence tests do not exist. Redis is not deployed.

## Production evolution

Adopt managed highly available PostgreSQL, per-service databases or strong isolation, automated backup and point-in-time recovery, connection pooling, encryption keys, monitored replicas, and managed Redis with explicit availability and eviction policies. Partition/archive high-volume movement history, monitor lock contention, reconcile balances against movement facts, and scale read projections independently without moving stock authority into a cache.

## Viva defence notes

Describe PostgreSQL as the source of truth and Redis as an optional derived optimization. Explain why cache introduction must follow measured need and documented consistency rules.
