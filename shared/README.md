# Shared

Contains deliberately small, versioned cross-service assets such as API/event schemas, observability conventions, and reusable test helpers. Domain logic remains within its owning service.

## Service foundation conventions

All ShopSphere FastAPI services follow these platform-foundation conventions:

- expose unversioned operational probes at `GET /health/live` and `GET /health/ready`;
- expose non-sensitive identity metadata at `GET /api/v1/info`;
- expose Prometheus text format at internal-only `GET /metrics` with a common bounded
  naming and label convention;
- identify public business APIs below `/api/v1` and document them through OpenAPI tags;
- use an application factory plus a module-level ASGI entry point;
- accept or generate `X-Request-ID`, return it on responses, and include it as
  `correlation_id` in JSON logs;
- use framework route templates for metrics and request logs rather than raw paths;
- prohibit customer, user, order, cart, product, email, JWT subject, correlation ID,
  token, credential, and raw path values from Prometheus labels;
- store and display environment configuration without committing secrets;
- return centralized error envelopes without exposing internal exception detail;
- keep domain, application, infrastructure, schema, and API responsibilities separated;
- remain independently testable, installable, and container-buildable;
- run containers as a numeric non-root user and provide a liveness health check.

Readiness reflects dependencies required for each implemented service to accept its
traffic. Optional Redis caching and asynchronous Kafka outbox delivery do not override
authoritative PostgreSQL health semantics. Metrics exposure is not a readiness
dependency and telemetry failure must not corrupt business transactions.

The exact metric contract, scrape security boundary, and cardinality rules are defined
in [Executive Operations and Observability Architecture](../docs/architecture/observability-architecture.md).

Shared code must earn its place through stable cross-service need. Domain models, database models, service configuration, and business rules must not be centralized here merely to reduce duplication.
