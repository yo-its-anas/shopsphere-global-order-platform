# ADR-004: Use FastAPI REST APIs with versioned `/api/v1` routes

## Status

Accepted — FastAPI service applications, customer, Catalogue, and Inventory versioned APIs, generated OpenAPI documents, fixed customer and Catalogue/Inventory gateway mappings, and an internal PoC gateway deployment are implemented. Wider domain routing, authenticated end-to-end gateway journeys, and formal API lifecycle governance remain Planned.

## Context

Synchronous module interactions and frontend journeys need clear, discoverable contracts. Python is mandated, and typed schema validation with generated API descriptions supports consistent service ownership.

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

Validate all inputs, constrain payloads, avoid sensitive error detail, preserve bearer credentials without logging them, and keep downstream service authorization authoritative. Production edge-token validation, rate limiting, and environment-appropriate OpenAPI exposure remain defence-in-depth controls rather than replacements for service authorization.

## PoC limitations

Versioning demonstrates contract discipline but not a mature multi-version support policy. The deployed internal gateway forwards explicit customer and Catalogue/Inventory paths, query parameters, bodies, correlation identifiers, and bearer headers, while each downstream service remains authoritative for JWT and domain authorization. An unauthenticated live catalogue request has confirmed the transport-to-backend authorization boundary; an authenticated end-to-end catalogue journey, gateway-side JWT defence in depth, quotas, circuit breaking, and other domain mappings remain Planned.

## Production evolution

Add API lifecycle ownership, consumer-driven compatibility tests, deprecation policy, gateway quotas, WAF controls, signed service identity, and formal schema publication.

## Viva defence notes

Explain that `/api/v1` versions the public contract rather than internal code. FastAPI was selected for typed Python development, OpenAPI support, and delivery speed, while events handle decoupled workflows.
