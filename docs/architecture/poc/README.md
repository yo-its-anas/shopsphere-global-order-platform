# PoC Architecture

Documents the architecture actually implemented on the single Ubuntu 22.04 VM and kind cluster, including limitations, diagrams, and deployment views.

## Customer identity boundary

The governing identity design is [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md), with service ownership defined by [ADR-001](../../adr/ADR-001-modular-microservices-architecture.md) and audit/log semantics defined by [ADR-010](../../adr/ADR-010-utc-timestamps-json-logs.md). It specifies the React-to-Keycloak Authorization Code with PKCE flow, the authenticated gateway-to-service flow, JWT validation, resource authorization, identity/profile mapping, audit handling, threat treatment, and credentials boundary.

The PoC deploys a single Keycloak pod backed by the internal PostgreSQL `keycloak_db`, with a sanitized `shopsphere` realm, governed roles, public frontend client, API audience, PKCE policy, security defaults, and event recording. Deployment and operational detail is documented in the [Keycloak PoC guide](../../../platform/kubernetes/overlays/poc/keycloak/README.md).

React, API gateway, customer-service, SMTP, MFA, and customer-profile integration remain Planned. The single-pod, single-node topology does not provide host-level high availability.
