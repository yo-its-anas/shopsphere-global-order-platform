# PoC Architecture

Documents the architecture actually implemented on the single Ubuntu 22.04 VM and kind cluster, including limitations, diagrams, and deployment views.

## Customer identity boundary

The governing identity design is [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md), with service ownership defined by [ADR-001](../../adr/ADR-001-modular-microservices-architecture.md) and audit/log semantics defined by [ADR-010](../../adr/ADR-010-utc-timestamps-json-logs.md). It specifies the React-to-Keycloak Authorization Code with PKCE flow, the authenticated gateway-to-service flow, JWT validation, resource authorization, identity/profile mapping, audit handling, threat treatment, and credentials boundary.

The [customer registration and profile provisioning sequence](customer-registration-sequence.md) shows the implemented React, Keycloak, gateway, and idempotent service boundaries while distinguishing source implementation from an executed end-to-end journey.

The [customer activity visibility design](customer-activity-visibility.md) distinguishes customer-domain audit history from real Keycloak authentication and user-administration events, including authorization, safe normalization, pagination, outage behavior, and the least-privilege Admin API trade-off.

The PoC deploys a single Keycloak pod backed by the internal PostgreSQL `keycloak_db`, with a sanitized `shopsphere` realm, governed roles, public frontend client, API audience, PKCE policy, security defaults, and event recording. Deployment and operational detail is documented in the [Keycloak PoC guide](../../../platform/kubernetes/overlays/poc/keycloak/README.md).

Customer-service implements JWT validation, resource authorization, profiles, addresses, domain auditing, concurrency-safe profile provisioning keyed by Keycloak `sub`, and a normalized domain-plus-Keycloak activity view. React implements Keycloak Authorization Code + PKCE, role-aware routes, and customer API screens. API Gateway implements fixed customer and Catalogue/Inventory route forwarding and bearer propagation. PostgreSQL, Keycloak, customer-service, catalogue-service, Redis, Kafka, and the internal API Gateway are deployed and Ready; the frontend is not deployed in the cluster.

Current validation confirms the single node, internal services, PostgreSQL PVC and logical databases, Keycloak policy/roles/events, least-privilege activity reader, customer-service probes, and frontend tests/build. It does not confirm the complete browser-to-service journey: the retained live integration report contains seven skips, and the customer-service test run did not complete during the documentation review.

PostgreSQL and Keycloak run as separate pods and logical databases but share the same kind node and physical GCP VM with customer-service. This consolidates every critical identity and data component into one host failure domain and does not provide host-level high availability.

## Catalogue and inventory boundary

The [Product Catalogue and Inventory domain design](../catalogue-inventory-domain-design.md) defines the Catalogue and Inventory bounded contexts within one PoC `catalogue-service`. PostgreSQL schema, internal business APIs, Redis cache-aside behavior, a transactional outbox, Kafka production, React screens, internal Kubernetes workloads, and fixed API Gateway transport mappings are implemented. Forty-eight backend tests, six focused frontend tests, and all 11 explicitly enabled authenticated live integration tests passed. Catalogue and gateway pods are Ready, live catalogue events reached `published` outbox state, and the principal administrator/customer browser journey passed. Order reservations and event consumers remain Planned.

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

This remains a design boundary for application behavior. The empty logical `order_db`
and dedicated `order_app` identity are provisioned on the shared PostgreSQL instance,
while `order-service` currently has only health and information endpoints. Cart/order
schemas, migrations, reservation commands, order gateway routes, React order screens,
order events, Kubernetes deployment, and domain validation remain Planned. The existing
Inventory schema has reserved balances and future movement names, but no callable
reservation/release/fulfilment interface.
