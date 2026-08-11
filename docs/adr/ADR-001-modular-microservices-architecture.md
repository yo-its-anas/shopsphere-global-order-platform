# ADR-001: Use a modular microservices architecture

## Status

Accepted — independently buildable service boundaries exist. Customer, Product Catalogue, and Inventory behavior are implemented; wider catalogue integrations remain Planned.

## Context

ShopSphere must demonstrate five enterprise modules with distinct responsibilities while remaining achievable within the capstone scope. Customer, catalogue, order, analytics, and gateway capabilities change for different reasons and require clear ownership.

## Decision

Organize the backend as independently bounded services: customer, catalogue, order, analytics, and API gateway. Keep domain logic and persistence ownership within each service. Use governed contracts in `shared/` only where interoperability requires them. Modular internal design is required even if PoC deployment constraints cause components to share infrastructure.

For the Customer Identity and Account Management capability, Keycloak owns authentication, credentials, password policy, token issuance, identity roles, login/logout, and authentication events. `customer-service` owns the customer business profile, addresses, account metadata, customer-domain audit history, and customer activity presentation. It links a profile to the immutable Keycloak subject identifier but does not store passwords, password hashes, reset tokens, or other credentials. The API gateway is the external API enforcement point; downstream services still enforce authorization for resources they own.

Within Product Catalogue and Inventory Management, `catalogue-service` is the PoC deployment boundary but contains two logical bounded contexts. Catalogue owns product metadata and lifecycle, category relationships, and effective-dated pricing. Inventory owns stock balances, reservations, derived availability, adjustments, immutable movement history, and inventory statistics. These contexts communicate through explicit application interfaces and must not share mutable domain objects merely because they share a process. The detailed model is defined in the [Product Catalogue and Inventory domain design](../architecture/catalogue-inventory-domain-design.md).

`order-service` will later own order lifecycle and request inventory reservations through a governed contract. It must never update catalogue or inventory tables directly. The contexts may separate into independently deployable services in production if scale, ownership, or change cadence justifies the additional distributed-system cost.

## Alternatives considered

- A single layered monolith: simpler deployment, but weaker demonstration of service ownership and independent evolution.
- Fine-grained microservices for every entity: excessive operational and integration cost for the capstone.
- Serverless functions: unsuitable for the required kind-based PoC and likely to fragment domain workflows.

## Consequences

Boundaries and ownership become explicit and services can evolve independently. The trade-off is additional API, event, deployment, observability, and consistency complexity. Cross-service database access is prohibited by design.

Identity lifecycle and customer-profile lifecycle are related but not identical. Their identifiers remain distinct, provisioning must tolerate retries and partial failure, and account deletion or suspension requires an explicit cross-boundary workflow rather than direct access to another component's data store.

Packaging Catalogue and Inventory together reduces PoC operations while preserving conceptual boundaries. It requires discipline in module dependencies and tests so the deployable unit does not become an unstructured shared model.

## Security implications

Each service requires least-privilege identity, network access, secrets, authorization, and audit controls. More network boundaries increase the attack surface and require consistent gateway and service-side validation.

## PoC limitations

Catalogue categories, products, effective pricing, search, inventory balances/movements/statistics, persistence adapters, migrations, internal APIs, RBAC enforcement, Redis cache-aside reads, a transactional Kafka outbox/producer, Kubernetes workloads, and service tests are implemented. Catalogue/Inventory API Gateway routes, Order Processing reservations, event consumers, and deployed authenticated end-to-end tests are not implemented. Services share a VM and supporting platforms, so the PoC does not prove independent infrastructure failure isolation or high availability.

## Production evolution

Deploy independently scalable workloads, enforce network policies and workload identity, isolate data ownership, formalize API/event compatibility, and apply service-level objectives and resilience patterns. Split Catalogue from Inventory only when measurable scale, reliability, team ownership, or release independence warrants separate operations.

## Viva defence notes

Defend the choice as a bounded, modular decomposition aligned to business capabilities—not microservices for their own sake. Explain that the modular monolith was credible, but the assessment requires demonstrating platform and distributed-system concerns while controlling service count.
