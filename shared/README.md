# Shared

Contains deliberately small, versioned cross-service assets such as API/event schemas, observability conventions, and reusable test helpers. Domain logic remains within its owning service.

## Service foundation conventions

All ShopSphere FastAPI services follow these Day 1 conventions:

- expose unversioned operational probes at `GET /health/live` and `GET /health/ready`;
- expose non-sensitive identity metadata at `GET /api/v1/info`;
- identify public business APIs below `/api/v1` and document them through OpenAPI tags;
- use an application factory plus a module-level ASGI entry point;
- accept or generate `X-Request-ID`, return it on responses, and include it as `correlation_id` in JSON logs;
- store and display environment configuration without committing secrets;
- return centralized error envelopes without exposing internal exception detail;
- keep domain, application, infrastructure, schema, and API responsibilities separated;
- remain independently testable, installable, and container-buildable;
- run containers as a numeric non-root user and provide a liveness health check.

Readiness means only that the current skeleton can serve requests. PostgreSQL, Redis, Kafka, Keycloak, downstream gateway routing, authentication, authorization, and business capabilities are not connected or claimed as complete. When dependencies are introduced, readiness checks must reflect only dependencies required to accept traffic and must use bounded timeouts.

Shared code must earn its place through stable cross-service need. Domain models, database models, service configuration, and business rules must not be centralized here merely to reduce duplication.
