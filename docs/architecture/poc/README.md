# PoC Architecture

Documents the architecture actually implemented on the single Ubuntu 22.04 VM and kind cluster, including limitations, diagrams, and deployment views.

## Customer identity boundary

The governing identity design is [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md), with service ownership defined by [ADR-001](../../adr/ADR-001-modular-microservices-architecture.md) and audit/log semantics defined by [ADR-010](../../adr/ADR-010-utc-timestamps-json-logs.md). It specifies the React-to-Keycloak Authorization Code with PKCE flow, the authenticated gateway-to-service flow, JWT validation, resource authorization, identity/profile mapping, audit handling, threat treatment, and credentials boundary.

The PoC target places Keycloak and application workloads on one single-node kind cluster. This is a design target only: identity configuration and integration are currently Planned, and the topology does not provide host-level high availability.
