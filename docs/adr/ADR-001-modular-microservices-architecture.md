# ADR-001: Use a modular microservices architecture

## Status

Proposed — service boundaries exist as Day 1 directories, but no deployable services or boundary tests exist yet.

## Context

ShopSphere must demonstrate five enterprise modules with distinct responsibilities while remaining achievable in seven days. Customer, catalogue, order, analytics, and gateway capabilities change for different reasons and require clear ownership.

## Decision

Organize the backend as independently bounded services: customer, catalogue, order, analytics, and API gateway. Keep domain logic and persistence ownership within each service. Use governed contracts in `shared/` only where interoperability requires them. Modular internal design is required even if PoC deployment constraints cause components to share infrastructure.

## Alternatives considered

- A single layered monolith: simpler deployment, but weaker demonstration of service ownership and independent evolution.
- Fine-grained microservices for every entity: excessive operational and integration cost for the capstone.
- Serverless functions: unsuitable for the required kind-based PoC and likely to fragment domain workflows.

## Consequences

Boundaries and ownership become explicit and services can evolve independently. The trade-off is additional API, event, deployment, observability, and consistency complexity. Cross-service database access is prohibited by design.

## Security implications

Each service requires least-privilege identity, network access, secrets, authorization, and audit controls. More network boundaries increase the attack surface and require consistent gateway and service-side validation.

## PoC limitations

The repository currently contains only service directories and responsibility READMEs. Services may share a VM and supporting platforms, so the PoC will not prove independent infrastructure failure isolation or high availability.

## Production evolution

Deploy independently scalable workloads, enforce network policies and workload identity, isolate data ownership, formalize API/event compatibility, and apply service-level objectives and resilience patterns.

## Viva defence notes

Defend the choice as a bounded, modular decomposition aligned to business capabilities—not microservices for their own sake. Explain that the modular monolith was credible, but the assessment requires demonstrating platform and distributed-system concerns while controlling service count.
