# PoC Architecture

Documents the architecture actually implemented on the single Ubuntu 22.04 VM and kind cluster, including limitations, diagrams, and deployment views.

## Customer identity boundary

The governing identity design is [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md), with service ownership defined by [ADR-001](../../adr/ADR-001-modular-microservices-architecture.md) and audit/log semantics defined by [ADR-010](../../adr/ADR-010-utc-timestamps-json-logs.md). It specifies the React-to-Keycloak Authorization Code with PKCE flow, the authenticated gateway-to-service flow, JWT validation, resource authorization, identity/profile mapping, audit handling, threat treatment, and credentials boundary.

The [customer registration and profile provisioning sequence](customer-registration-sequence.md) shows the implemented React, Keycloak, gateway, and idempotent service boundaries while distinguishing source implementation from an executed end-to-end journey.

The [customer activity visibility design](customer-activity-visibility.md) distinguishes customer-domain audit history from real Keycloak authentication and user-administration events, including authorization, safe normalization, pagination, outage behavior, and the least-privilege Admin API trade-off.

The PoC deploys a single Keycloak pod backed by the internal PostgreSQL `keycloak_db`, with a sanitized `shopsphere` realm, governed roles, public frontend client, API audience, PKCE policy, security defaults, and event recording. Deployment and operational detail is documented in the [Keycloak PoC guide](../../../platform/kubernetes/overlays/poc/keycloak/README.md).

Customer-service implements JWT validation, resource authorization, profiles, addresses, domain auditing, concurrency-safe profile provisioning keyed by Keycloak `sub`, and a normalized domain-plus-Keycloak activity view. React implements Keycloak Authorization Code + PKCE, role-aware routes, and customer API screens. API Gateway implements fixed customer, Catalogue/Inventory, and Order route forwarding and bearer propagation. PostgreSQL, Keycloak, customer-service, catalogue-service, order-service, Redis, Kafka, and the internal API Gateway are deployed and Ready; the frontend is not deployed in the cluster.

Current validation confirms the single node, internal services, PostgreSQL PVC and logical databases, Keycloak policy/roles/events, least-privilege activity reader, customer-service probes, and frontend tests/build. It does not confirm the complete browser-to-service journey: the retained live integration report contains seven skips, and the customer-service test run did not complete during the documentation review.

PostgreSQL and Keycloak run as separate pods and logical databases but share the same kind node and physical GCP VM with customer-service. This consolidates every critical identity and data component into one host failure domain and does not provide host-level high availability.

## Catalogue and inventory boundary

The [Product Catalogue and Inventory domain design](../catalogue-inventory-domain-design.md) defines the Catalogue and Inventory bounded contexts within one PoC `catalogue-service`. PostgreSQL schema, internal business APIs, Redis cache-aside behavior, a transactional outbox, Kafka production, React screens, internal Kubernetes workloads, and fixed public API Gateway transport mappings are implemented. Sixty backend tests pass, including reservation concurrency/idempotency/cache/outbox coverage. Six focused frontend tests and all 11 explicitly enabled authenticated live integration tests passed for the catalogue scope. Catalogue and gateway pods were Ready, live catalogue events reached `published` outbox state, and the principal administrator/customer browser journey passed. The reservation migration, topics, dedicated service identity and Order reserve/release integration are now Platform Validated; event consumers and automatic reservation expiry remain Planned.

PostgreSQL is the sole transactional source of truth. Redis is an ephemeral performance
optimization, and Kafka transports asynchronous facts after the authoritative commit.
This PoC uses one PostgreSQL instance, one Redis instance, one Kafka broker/controller,
one kind node and one physical VM; it provides no host-level high availability.

## Order Processing boundary

The [Enterprise Order Processing domain design](../order-processing-domain-design.md)
defines the target ownership, lifecycle, immutable order snapshot, idempotent checkout,
and reservation-based Saga. [ADR-011](../../adr/ADR-011-reservation-based-order-saga.md)
records the decision to obtain an authoritative synchronous quote/reservation from
Catalogue while publishing post-commit facts through transactional outboxes.

The logical `order_db` and dedicated `order_app` identity are provisioned on the shared
PostgreSQL instance. Order-service implements customer-owned carts, authoritative
re-quotation, idempotent checkout, immutable order snapshots, controlled lifecycle and
cancellation, audit/status history, Saga compensation, and a transactional outbox.
Catalogue owns row-locked inventory reservations and release/consume transitions. A
dedicated Keycloak confidential service account carries only the `order_service` role.

The service is deployed internally with a ClusterIP, hardened pod security context and
PostgreSQL-only readiness gate. The live simulated-customer platform smoke passed through
API Gateway, created and cancelled an order, released its reservation, and observed
broker-acknowledged `order.created.v1`, `order.confirmed.v1`,
`order.status_changed.v1`, and `order.cancelled.v1` outbox events. This is gateway/platform
integration evidence. React cart, checkout, confirmation, own-history/detail/timeline and
role-aware order-management screens are implemented and component-tested. The separate
API-driven E2E suite passed prerequisites and scenarios A–I through the deployed Gateway;
a retained browser-driven order journey is Pending / Not Verified.

Customer, catalogue and order workloads share one physical GCP VM and one Kubernetes
node. Their logical databases share one PostgreSQL server; Kafka is a single broker and
Redis a single instance. Inventory reservation and order creation are separate service
transactions coordinated by Saga compensation rather than a distributed transaction.
This topology has no infrastructure-level high availability.

## Executive operations and observability boundary

The [Executive Operations and Observability Architecture](../observability-architecture.md)
defines four separate concerns: business, application, infrastructure, and security
observability. Domain services retain KPI authority: Customer owns provisioned-profile
counts, Catalogue/Inventory owns product and stock aggregates, and Order owns processed
orders, simulated order value, and fulfilment status. Analytics-service remains a
health/info skeleton and the React executive dashboard remains explicitly mock data.

UTC JSON logs, correlation IDs, health/readiness endpoints, Kubernetes probes, resource
limits, domain audit, and transactional-outbox evidence exist. Prometheus, Grafana,
OpenTelemetry, Loki, Wazuh, live analytics, telemetry dashboards, and alert rules are not
deployed or validated. If implemented locally, they will share the only VM/node and its
resource/failure domain. A complete VM failure could remove both applications and their
local monitoring; independent detection requires an external heartbeat or monitoring
location.
