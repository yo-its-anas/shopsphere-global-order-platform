# ADR-006: Use PostgreSQL for transactional data and Redis for caching

## Status

Proposed — environment placeholders exist, but schemas, migrations, clients, containers, and persistence tests do not.

## Context

Customer, catalogue, order, and reporting workflows need reliable relational persistence. Selected read paths may benefit from low-latency caching, but cached data must not become an ungoverned source of truth.

## Decision

Use PostgreSQL as the authoritative transactional datastore with SQLAlchemy and Alembic. Preserve logical ownership of service data even if the PoC consolidates database infrastructure. Use Redis only for explicitly bounded cache or ephemeral coordination use cases, with expiry and invalidation rules.

## Alternatives considered

- MySQL: capable, but PostgreSQL provides a strong open-source relational and extensibility baseline.
- MongoDB as the primary store: flexible documents but a weaker default fit for transactional order relationships.
- Redis as primary persistence: inappropriate for authoritative transactional records.
- No cache: simpler and remains acceptable until measured performance justifies caching.

## Consequences

Transactional integrity and migration history become explicit. Redis can improve latency but introduces invalidation, staleness, and failure-mode complexity. Services must not join across one another's owned schemas directly.

## Security implications

Use separate least-privilege database identities, encrypted connections, protected networks, parameterized SQL, encrypted backups, audited administrative access, and secrets outside source control. Redis must not be publicly reachable or store unnecessary sensitive data.

## PoC limitations

Single instances provide no high availability and may share host resources. Backup restoration, failover, replica behavior, and realistic cache pressure are not proven. Runtime data integrations remain unimplemented beyond configuration placeholders.

## Production evolution

Adopt managed highly available PostgreSQL, per-service databases or strong isolation, automated backup and point-in-time recovery, connection pooling, encryption keys, monitored replicas, and managed Redis with explicit availability and eviction policies.

## Viva defence notes

Describe PostgreSQL as the source of truth and Redis as an optional derived optimization. Explain why cache introduction must follow measured need and documented consistency rules.
