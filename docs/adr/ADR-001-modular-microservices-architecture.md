# ADR-001: Use a modular microservices architecture

## Status

Accepted — independently buildable service boundaries exist. Customer, Product
Catalogue/Inventory, and Enterprise Order Processing behavior are implemented; Analytics
remains a foundation rather than a completed business capability.

## Context

ShopSphere must demonstrate five enterprise modules with distinct responsibilities while remaining achievable within the capstone scope. Customer, catalogue, order, analytics, and gateway capabilities change for different reasons and require clear ownership.

## Decision

Organize the backend as independently bounded services: customer, catalogue, order, analytics, and API gateway. Keep domain logic and persistence ownership within each service. Use governed contracts in `shared/` only where interoperability requires them. Modular internal design is required even if PoC deployment constraints cause components to share infrastructure.

For the Customer Identity and Account Management capability, Keycloak owns authentication, credentials, password policy, token issuance, identity roles, login/logout, and authentication events. `customer-service` owns the customer business profile, addresses, account metadata, customer-domain audit history, and customer activity presentation. It links a profile to the immutable Keycloak subject identifier but does not store passwords, password hashes, reset tokens, or other credentials. The API gateway is the external API enforcement point; downstream services still enforce authorization for resources they own.

Within Product Catalogue and Inventory Management, `catalogue-service` is the PoC deployment boundary but contains two logical bounded contexts. Catalogue owns product metadata and lifecycle, category relationships, and effective-dated pricing. Inventory owns stock balances, reservations, derived availability, adjustments, immutable movement history, and inventory statistics. These contexts communicate through explicit application interfaces and must not share mutable domain objects merely because they share a process. The detailed model is defined in the [Product Catalogue and Inventory domain design](../architecture/catalogue-inventory-domain-design.md).

`order-service` owns carts, orders, immutable commercial snapshots, lifecycle, status
history, transaction audit, checkout idempotency, Saga state, and the order-event
boundary. Catalogue and Inventory remain authoritative for sellable products, prices,
availability, reservations, releases, and fulfilment consumption. Order-service never
updates catalogue or inventory tables directly. Checkout implements the governed
reservation Saga in [ADR-011](ADR-011-reservation-based-order-saga.md), detailed by the
[Enterprise Order Processing domain design](../architecture/order-processing-domain-design.md).

`analytics-service` is a read-only composition boundary for executive business
operations. Customer-service owns registration/profile aggregates, Catalogue/Inventory
owns product and stock aggregates, and Order owns order, simulated-value, and fulfilment
aggregates. Analytics-service must use governed owner APIs for current views or
rebuildable idempotent event projections for historical scale; it must not query or write
another service's database. Operational metrics, logs, traces, and Wazuh security events
remain separate from business KPI authority as defined by [ADR-012](ADR-012-layered-observability-source-owned-kpis.md).

## Alternatives considered

- A single layered monolith: simpler deployment, but weaker demonstration of service ownership and independent evolution.
- Fine-grained microservices for every entity: excessive operational and integration cost for the capstone.
- Serverless functions: unsuitable for the required kind-based PoC and likely to fragment domain workflows.

## Consequences

Boundaries and ownership become explicit and services can evolve independently. The trade-off is additional API, event, deployment, observability, and consistency complexity. Cross-service database access is prohibited by design.

Identity lifecycle and customer-profile lifecycle are related but not identical. Their identifiers remain distinct, provisioning must tolerate retries and partial failure, and account deletion or suspension requires an explicit cross-boundary workflow rather than direct access to another component's data store.

Packaging Catalogue and Inventory together reduces PoC operations while preserving conceptual boundaries. It requires discipline in module dependencies and tests so the deployable unit does not become an unstructured shared model.

Order checkout adds an unavoidable consistency boundary. The selected Saga keeps each
service transaction local, makes compensating release and uncertain outcomes explicit,
and uses transactional outboxes for asynchronous facts rather than treating Kafka as a
distributed transaction coordinator.

## Security implications

Each service requires least-privilege identity, network access, secrets, authorization, and audit controls. More network boundaries increase the attack surface and require consistent gateway and service-side validation.

## PoC limitations

Catalogue/Inventory and Order schemas, APIs, RBAC, reservations, Saga/outboxes, Kafka
producers, fixed Gateway routes, React screens and Kubernetes workloads are implemented.
The API-driven Order E2E suite passed scenarios A–I with simulated data, including
final-unit concurrency, compensation and Kafka recovery. Services and their logical
databases share one VM, node and PostgreSQL server, so the PoC does not prove independent
infrastructure failure isolation or high availability. Durable automatic reconciliation,
reservation expiry and resilient event consumers are not implemented.

## Production evolution

Deploy independently scalable workloads, enforce network policies and workload identity, isolate data ownership, formalize API/event compatibility, and apply service-level objectives and resilience patterns. Split Catalogue from Inventory only when measurable scale, reliability, team ownership, or release independence warrants separate operations.

## Viva defence notes

Defend the choice as a bounded, modular decomposition aligned to business capabilities—not microservices for their own sake. Explain that the modular monolith was credible, but the assessment requires demonstrating platform and distributed-system concerns while controlling service count.
