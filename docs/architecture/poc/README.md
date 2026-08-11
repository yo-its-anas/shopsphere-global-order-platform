# PoC Architecture

Documents the architecture actually implemented on the single Ubuntu 22.04 VM and kind cluster, including limitations, diagrams, and deployment views.

## Customer identity boundary

The governing identity design is [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md), with service ownership defined by [ADR-001](../../adr/ADR-001-modular-microservices-architecture.md) and audit/log semantics defined by [ADR-010](../../adr/ADR-010-utc-timestamps-json-logs.md). It specifies the React-to-Keycloak Authorization Code with PKCE flow, the authenticated gateway-to-service flow, JWT validation, resource authorization, identity/profile mapping, audit handling, threat treatment, and credentials boundary.

The [customer registration and profile provisioning sequence](customer-registration-sequence.md) shows the implemented React, Keycloak, gateway, and idempotent service boundaries while distinguishing source implementation from an executed end-to-end journey.

The [customer activity visibility design](customer-activity-visibility.md) distinguishes customer-domain audit history from real Keycloak authentication and user-administration events, including authorization, safe normalization, pagination, outage behavior, and the least-privilege Admin API trade-off.

The PoC deploys a single Keycloak pod backed by the internal PostgreSQL `keycloak_db`, with a sanitized `shopsphere` realm, governed roles, public frontend client, API audience, PKCE policy, security defaults, and event recording. Deployment and operational detail is documented in the [Keycloak PoC guide](../../../platform/kubernetes/overlays/poc/keycloak/README.md).

Customer-service implements JWT validation, resource authorization, profiles, addresses, domain auditing, concurrency-safe profile provisioning keyed by Keycloak `sub`, and a normalized domain-plus-Keycloak activity view. React implements Keycloak Authorization Code + PKCE, role-aware routes, and customer API screens. API Gateway implements fixed customer route forwarding and bearer propagation. PostgreSQL, Keycloak, and customer-service are deployed and Ready; API Gateway and frontend are not deployed in the cluster.

Current validation confirms the single node, internal services, PostgreSQL PVC and logical databases, Keycloak policy/roles/events, least-privilege activity reader, customer-service probes, and frontend tests/build. It does not confirm the complete browser-to-service journey: the retained live integration report contains seven skips, and the customer-service test run did not complete during the documentation review.

PostgreSQL and Keycloak run as separate pods and logical databases but share the same kind node and physical GCP VM with customer-service. This consolidates every critical identity and data component into one host failure domain and does not provide host-level high availability.

## Catalogue and inventory boundary

The [Product Catalogue and Inventory domain design](../catalogue-inventory-domain-design.md) defines the proposed Catalogue and Inventory bounded contexts within one PoC `catalogue-service`. No catalogue database, domain schema, business API, gateway mapping, Redis/Kafka integration, or Kubernetes workload is implemented, so this is design evidence only.
