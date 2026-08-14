# Production Architecture

Documents the recommended scalable, resilient, secure, and operable future state. It must clearly distinguish recommendations from implemented evidence.

## Customer identity evolution

The production identity direction is governed by the production-evolution section of [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md). It retains the separation between identity credentials and customer-domain data while adding resilient identity hosting, stronger authentication, lifecycle automation, protected administration, durable audit handling, privacy controls, monitoring, recovery, and formally governed authorization. These are recommendations, not implemented evidence.

Unlike the PoC, production must not place the only identity provider and only transactional database on one physical host. Use a supported multi-instance Keycloak topology or evaluated managed identity service across independent failure domains. Store identity and customer data in separately governed, regional managed PostgreSQL services or equivalent isolated databases with replication, encrypted automated backups, point-in-time recovery, tested failover, and explicit recovery objectives.

Production also requires private administrative access, TLS throughout exposed paths, external secret management and rotation, phishing-resistant MFA, verified-email and recovery delivery, durable privacy-governed identity-event export, immutable domain-audit retention, rate limiting, abuse monitoring, capacity testing, and disaster-recovery exercises. Merely increasing replicas inside the single-node PoC would not satisfy these requirements.

## Catalogue and inventory evolution

The [Product Catalogue and Inventory domain design](../catalogue-inventory-domain-design.md) preserves separate Catalogue and Inventory ownership while allowing one PoC deployment. Production may split these contexts when independently measured scale, availability, ownership, or release cadence warrants it. Inventory requires managed regional/high-availability PostgreSQL, encrypted automated backups, PITR, tested failover, contention monitoring, reconciliation and durable movement history. Search, statistics and Redis-based views remain disposable projections; Redis should be replicated across zones with TLS, authentication and automatic failover.

The PoC transactional outbox and producer must evolve to managed or multi-broker Kafka
across zones, replicated topics, durable encrypted storage, governed schemas, TLS,
least-privilege ACLs, monitored relay lag and independently idempotent consumers. Run
application workloads on multiple Kubernetes nodes/zones with disruption budgets,
measured horizontal autoscaling, private connectivity, workload identity, external
secret management, and enforced network/ingress/egress policy. These are production
recommendations, not evidence that the current single-VM PoC is highly available.

## Order Processing evolution

The target order boundary is defined in the
[Enterprise Order Processing domain design](../order-processing-domain-design.md). A
production implementation retains Order-owned persistence and Catalogue-owned inventory
while evolving the PoC Saga into a durable, observable workflow with reservation leases,
durable reconciliation workers, independently managed regional/HA PostgreSQL, and a
horizontally scalable stateless order-service on multi-zone GKE behind managed load
balancing. Use autoscaling, replicated/managed Redis for disposable projections,
managed multi-broker Kafka, resilient idempotent event consumers, stronger service
identity and mTLS/private service traffic where appropriate, and tested disaster
recovery. A multi-region strategy should be introduced only where measured latency,
availability, recovery and data-residency requirements justify its consistency and
operational complexity. Payment, tax, fraud, fulfilment, and notification remain
separately governed capabilities rather than fields casually added to the Order
aggregate. These are recommendations, not implemented capabilities.

## Executive operations and observability evolution

The production direction follows the
[Executive Operations and Observability Architecture](../observability-architecture.md)
and [ADR-012](../../adr/ADR-012-layered-observability-source-owned-kpis.md). Preserve
source-owned business KPI definitions while scaling analytics with governed,
idempotent event-derived read models and reconciliation. Keep the executive application
surface distinct from the engineering Grafana surface.

Run services on multi-zone GKE with horizontally scaled dedicated OpenTelemetry
collectors and node agents. Export to managed/external metrics, durable object-backed log
and trace stores, protected Grafana, and alert routing outside the application failure
domain. Define SLIs/SLOs, multi-window burn-rate alerts, long-term retention, tested
telemetry recovery, and stable autoscaling signals. Use a centralized SIEM for governed
Wazuh, identity, cloud, and Kubernetes security telemetry.

Production monitoring requires access isolation, encryption, workload identity/mTLS
where appropriate, external secret management, capacity/cardinality governance,
multi-zone availability, disaster recovery, and on-call/runbook ownership. A
multi-region telemetry and analytics strategy should be introduced only for explicit
availability, recovery, latency, or residency requirements.
