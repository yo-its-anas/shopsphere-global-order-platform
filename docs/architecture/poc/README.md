# PoC Architecture

Documents the architecture actually implemented on the single Ubuntu 22.04 VM and kind cluster, including limitations, diagrams, and deployment views.

## Customer identity boundary

The governing identity design is [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md), with service ownership defined by [ADR-001](../../adr/ADR-001-modular-microservices-architecture.md) and audit/log semantics defined by [ADR-010](../../adr/ADR-010-utc-timestamps-json-logs.md). It specifies the React-to-Keycloak Authorization Code with PKCE flow, the authenticated gateway-to-service flow, JWT validation, resource authorization, identity/profile mapping, audit handling, threat treatment, and credentials boundary.

The [customer registration and profile provisioning sequence](customer-registration-sequence.md) shows the implemented idempotent service boundary and clearly identifies the planned React and gateway integration steps.

The PoC deploys a single Keycloak pod backed by the internal PostgreSQL `keycloak_db`, with a sanitized `shopsphere` realm, governed roles, public frontend client, API audience, PKCE policy, security defaults, and event recording. Deployment and operational detail is documented in the [Keycloak PoC guide](../../../platform/kubernetes/overlays/poc/keycloak/README.md).

Customer-service now implements JWT validation, resource authorization, profiles, addresses, domain auditing, and concurrency-safe profile provisioning keyed by Keycloak `sub`. React OIDC integration, API-gateway routing, workload deployment, SMTP, MFA, and executed browser-to-service journeys remain Planned. The single-pod, single-node topology does not provide host-level high availability.
