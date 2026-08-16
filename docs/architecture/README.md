# Architecture Maps & Decisions

This directory contains the authoritative domain designs, decision records, and platform maps for the ShopSphere Enterprise Platform PoC. It cleanly separates single-node sandbox constraints from recommended future-state production architectures.

---

## 1. Capability & Domain Designs

*   [Product Catalogue and Inventory Domain Design](catalogue-inventory-domain-design.md) — Maps implemented catalogue/inventory aggregates, invariants, pricing history, authorization controls, concurrency safeguards, and transactional outboxes.
*   [Enterprise Order Processing Domain Design](order-processing-domain-design.md) — Maps customer-owned carts, immutable order snapshots, synchronous reservation Sagas, checkout idempotency keys, status lifecycles, and transaction audit trails.

---

## 2. Platform Observability & Security Designs (Upgraded)

*   [Observability & Operations Architecture](observability-architecture.md) — Governs the multi-tiered visibility layout. Strictly separates **Executive Dashboard** (business KPIs), **Grafana** (SRE technical metrics & Loki logs), and **Wazuh** (security monitoring).
*   [Centralized Loki Ingestion & Logging](loki-logging-poc-and-evolution.md) — Maps the structured Promtail DaemonSet log harvesting flow, showing how correlation IDs and trace IDs are propagated across microservices without exposing credentials.
*   [Grafana Dashboard Operations](grafana-dashboards-and-operations.md) — Details the secure provisioned datasources and pre-configured golden-signals dashboards.
*   [Wazuh Security Monitoring SIEM](wazuh-security-monitoring.md) — Documents the containerized sandboxed SIEM agent and manager integration, explicitly distinguishing VM host-level coverage from container-level capabilities.

---

## 3. Architecture Decision Records (ADRs)

Refer to [docs/adr/README.md](../adr/README.md) to review the authoritative Architecture Decision Records (ADRs 001–012) governing microservice boundaries, UTC structured logging, single-node kind topologies, keycloak RBAC, and reservation-based checkout flows.
