# Recommended Migration Strategy

> **CRITICAL ARCHITECTURAL WARNING**
>
> **THIS DOCUMENT DESCRIBES A THEORETICAL MIGRATION STRATEGY TO PRODUCTION.**
> **THIS IS NOT IMPLEMENTED IN THE CURRENT SINGLE-VM PROOF-OF-CONCEPT (POC).**

This document outlines the phased approach to transition ShopSphere Global from its current single-node Proof-of-Concept (PoC) into a fully managed, globally scalable production environment on Google Cloud.

---

## Phase 1: Proof-of-Concept (Current State)

The platform is currently operating in its foundational state.
*   **Infrastructure:** Single Ubuntu VM running Docker and a `kind` cluster.
*   **Data Services:** Self-hosted PostgreSQL, Redis, and Kafka running as StatefulSets within the same cluster.
*   **Observability:** Ephemeral, self-hosted Prometheus, Grafana, and Loki.
*   **Limitations:** Single point of failure (SPOF), no high availability, resource contention under load, and no durable backups.

## Phase 2: Managed GKE Foundation & Externalized Data Services

The primary objective of Phase 2 is to decouple stateless compute from stateful data storage to eliminate data loss risks.
*   **GKE Migration:** Provision a regional Google Kubernetes Engine (GKE) cluster. Re-deploy the API Gateway, Customer, Catalogue, Order, and Analytics services to GKE.
*   **Externalize PostgreSQL:** Migrate the `customer_db`, `catalogue_db`, and `order_db` schemas to Google Cloud SQL (PostgreSQL). Implement automated daily backups.
*   **Externalize Redis:** Provision Google Cloud Memorystore for Redis and update the Catalogue service connection string.
*   **Externalize Kafka:** Provision Confluent Cloud or Google Cloud Managed Service for Apache Kafka. Create the `order.created` topics with proper retention policies.
*   **Outcome:** Applications are now resilient to pod restarts and node failures, with state securely managed by Google Cloud.

## Phase 3: High Availability (HA) & Autoscaling

Phase 3 focuses on ensuring the platform can survive zone outages and scale dynamically with user traffic.
*   **Cloud SQL HA:** Enable Multi-AZ Regional HA on the Cloud SQL instance to provide synchronous replication and automatic failover.
*   **Node Pools & Multi-Zone GKE:** Ensure GKE worker nodes are spread across at least three Availability Zones.
*   **Horizontal Pod Autoscaling (HPA):** Configure HPA for the core microservices based on CPU utilization and custom HTTP throughput metrics.
*   **Cluster Autoscaler:** Enable the GKE Cluster Autoscaler to automatically provision new VM instances when pod demand exceeds current capacity.
*   **Outcome:** The platform can survive the loss of an entire datacenter zone without downtime and gracefully absorb traffic spikes.

## Phase 4: Centralized Observability & Security

Phase 4 hardens the platform's visibility and threat defense perimeters.
*   **Centralized Telemetry:** Decommission the in-cluster Prometheus and Loki instances. Transition OpenTelemetry Collectors to export metrics, logs, and traces directly to Google Cloud Operations Suite (Cloud Monitoring/Logging).
*   **Secret Management:** Migrate Kubernetes Secrets to Google Secret Manager, accessing them securely via Workload Identity.
*   **WAF & Edge Security:** Deploy Google Cloud Armor and a Global External HTTP(S) Load Balancer to terminate TLS and block malicious web traffic (e.g., DDoS, SQLi).
*   **Centralized SIEM:** Route Wazuh alerts and GCP Audit Logs to a centralized SIEM (like Splunk or Chronicle) for SOC analysis.
*   **Outcome:** SREs gain durable, multi-year compliance retention for logs and proactive alerting based on strict Service Level Objectives (SLOs).

## Phase 5: Multi-Region Readiness

The final phase prepares ShopSphere for global scale and disaster recovery.
*   **Cross-Region Read Replicas:** Deploy Cloud SQL read replicas in secondary regions to serve low-latency Catalogue queries to international users.
*   **Multi-Region GKE:** Deploy a secondary, active-passive GKE cluster in another continent for geographic failover.
*   **Global Anycast Routing:** Use Cloud DNS and Global Load Balancing to route users to their closest healthy regional cluster.
*   **Outcome:** The platform achieves enterprise-grade disaster recovery capabilities with RTOs measured in minutes.

---

## Viva-Ready Architecture Trade-offs

*   **Big Bang vs. Phased Migration:**
    *   *Trade-off:* We strongly recommend a phased migration. A "Big Bang" approach (moving compute, data, and edge routing simultaneously) introduces unacceptable risk and makes rollback nearly impossible. Phased migration allows SREs to validate data integrity (Phase 2) before introducing complex autoscaling rules (Phase 3).
*   **Managed Services Migration Cost:**
    *   *Trade-off:* Moving from in-cluster Postgres to Cloud SQL requires a brief planned downtime maintenance window to perform a final data dump/restore or configure logical replication. We accept this one-time downtime to secure long-term durability.