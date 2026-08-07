# ADR-004: Use FastAPI REST APIs with versioned `/api/v1` routes

## Status

Proposed — no FastAPI application, route, or OpenAPI specification exists yet.

## Context

Synchronous module interactions and frontend journeys need clear, discoverable contracts. Python is mandated, and the short delivery period benefits from schema validation and generated API descriptions.

## Decision

Implement synchronous service interfaces with FastAPI and REST semantics. Externally supported routes begin with `/api/v1`. Use typed request and response models, consistent error envelopes, correlation identifiers, pagination conventions, and generated OpenAPI documents.

## Alternatives considered

- Django REST Framework: mature but heavier than required for focused services.
- Flask: flexible, but requires more manual schema and documentation integration.
- GraphQL: useful for flexible queries but adds schema, authorization, caching, and gateway complexity.
- gRPC: strong internal contracts but less direct for browser-facing assessment workflows.

## Consequences

Contracts are approachable and automatically describable. Versioned paths support controlled breaking changes, but API lifecycle governance and compatibility testing are still required. REST does not replace asynchronous events.

## Security implications

Validate all inputs, constrain payloads, avoid sensitive error detail, enforce authorization at gateway and service layers, rate-limit exposed routes, and ensure OpenAPI exposure is appropriate for each environment.

## PoC limitations

Versioning will demonstrate contract discipline but not a mature multi-version support policy. There are currently no routes or contract tests.

## Production evolution

Add API lifecycle ownership, consumer-driven compatibility tests, deprecation policy, gateway quotas, WAF controls, signed service identity, and formal schema publication.

## Viva defence notes

Explain that `/api/v1` versions the public contract rather than internal code. FastAPI was selected for typed Python development, OpenAPI support, and delivery speed, while events handle decoupled workflows.
