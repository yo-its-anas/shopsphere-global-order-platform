# Recommended Production Enterprise Architecture

> **CRITICAL ARCHITECTURAL WARNING**
>
> **THIS DOCUMENT DESCRIBES A THEORETICAL RECOMMENDED PRODUCTION ARCHITECTURE.**
> **THIS IS NOT IMPLEMENTED IN THE CURRENT SINGLE-VM PROOF-OF-CONCEPT (POC).**

This document outlines the professional, cloud-scale architecture design for ShopSphere Global, targeting Google Cloud Platform (GCP). It transforms the functional baseline established in the PoC into a highly available, resilient, and secure enterprise platform.

---

## 1. Edge & Networking

To secure inbound traffic and optimize global delivery, the edge tier completely shields the internal cluster:
*   **Global Cloud DNS:** Provides highly available anycast DNS routing.
*   **Cloud CDN:** Caches static frontend assets and public-facing catalogue imagery at edge PoPs globally, reducing origin load.
*   **Cloud Armor (WAF):** Enforces rate limiting, geography-based filtering, and OWASP Top 10 protection before traffic ever reaches the cluster.
*   **Global External Application Load Balancer:** Terminates TLS (SSL certificates), negotiates modern cipher suites, and performs anycast routing to the nearest healthy backend region.

## 2. Kubernetes (GKE)

The compute foundation transitions from a single-node sandbox to a managed, multi-zone Google Kubernetes Engine (GKE) cluster.
*   **Regional / Multi-Zone GKE:** Control plane and worker nodes are distributed across at least 3 Availability Zones (e.g., `europe-west2-a`, `b`, `c`) to survive zone failures.
*   **Dedicated Node Pools:** Segregates workloads logically (e.g., General Compute, High-Memory for cache-heavy workloads).
*   **Horizontal Pod Autoscaling (HPA) & Cluster Autoscaler:** Pods scale automatically based on custom metrics (e.g., HTTP request rate, Kafka lag) rather than just CPU/Memory. The Cluster Autoscaler adds underlying compute nodes when pods are pending.
*   **Resiliency Primitives:** `PodDisruptionBudgets` (PDBs) guarantee minimum available replicas during node upgrades. `topologySpreadConstraints` ensure replicas are evenly spread across availability zones.
*   **Workload Identity:** Pods authenticate directly to GCP services (e.g., KMS, Secret Manager) using Google IAM Service Accounts, eliminating the need to mount static JSON keys.

## 3. Microservices & API Gateway

Services are entirely stateless, enabling seamless horizontal scaling.
*   **Ingress & API Gateway:** Uses a robust Ingress Controller (e.g., GKE Ingress or an API Gateway like Apigee/Kong) for secure routing, OAuth2 validation delegation, and centralized CORS policies.
*   **Internal Communication:** Uses native Kubernetes DNS or a Service Mesh (e.g., Anthos Service Mesh/Istio) for mTLS encryption between pods.
*   **Resiliency Patterns:** Service calls implement strict timeouts, bounded exponential backoff retries, and Circuit Breakers to prevent cascading failures if a downstream dependency (like a database) stalls.

## 4. Managed Datastores

### 4.1 Cloud SQL for PostgreSQL
*   **High Availability (HA):** Configured for Multi-AZ Regional HA with synchronous replication. If the primary zone fails, Cloud SQL automatically promotes the standby instance.
*   **Read Replicas:** Read-heavy workloads (like the catalogue) leverage asynchronous read replicas deployed in different zones/regions.
*   **Backups & PITR:** Automated daily backups and Write-Ahead Log (WAL) archiving provide Point-in-Time Recovery (PITR) down to the minute.
*   **Connection Pooling:** Cloud SQL Auth proxy or PgBouncer handles connection multiplexing to prevent Postgres process starvation under horizontal pod scaling.

### 4.2 Memorystore for Redis
*   **Managed HA Redis:** Deployed using the Standard Tier (High Availability), which provisions a primary and a synchronous replica across different zones with automated failover.

### 4.3 Managed Kafka
*   **Multi-Broker Eventing:** Use Google Cloud Managed Service for Apache Kafka or Confluent Cloud.
*   **Resilience:** Brokers are distributed across 3 zones. Topics are configured with a `replication.factor=3` and `min.insync.replicas=2`.
*   **Governance:** Implement a Schema Registry to enforce strict evolution policies for domain events (e.g., `order.created`).

## 5. Identity & Access Management (IAM)

*   **Production Keycloak:** Run Keycloak in an HA active-active cluster backed by Cloud SQL, or evaluate migrating to a fully managed identity solution (e.g., Google Identity Platform or Auth0) to offload the burden of operating complex identity infrastructure.

## 6. Security & DevSecOps

*   **Secret Manager & KMS:** All application secrets are stored centrally in Google Secret Manager and fetched at runtime via Workload Identity. Application-level encryption uses Google Cloud KMS.
*   **Private Networking:** GKE clusters are deployed as VPC-native Private Clusters. Nodes have no public IP addresses. Outbound traffic routes through Cloud NAT.
*   **Network Policies:** Zero-trust cluster networking. Pods can only communicate if explicitly allowed via Calico/Cilium `NetworkPolicy` manifests.
*   **Centralized SIEM:** Integrate host, network, and application security events into a centralized Security Command Center (SCC) or external SIEM (e.g., Splunk/Wazuh HA) for continuous vulnerability management.

## 7. Observability

*   **External Telemetry:** Ephemeral local storage is eliminated. All metrics and logs stream to highly durable external platforms (e.g., Google Cloud Monitoring/Logging, Datadog).
*   **Long-Term Retention:** Audit logs and compliance metrics are archived to low-cost Cloud Storage (GCS) buckets for multi-year retention.
*   **Tracing:** OpenTelemetry routes spans to Cloud Trace or Grafana Tempo for deep cross-service bottleneck analysis.
*   **SLO/SLI Alerting:** Alerts are driven by user-impacting Service Level Indicators (SLIs), such as "99.9% of checkouts must succeed within 2 seconds." Alertmanager routes critical pages to Opsgenie or PagerDuty.

---

## 8. Viva-Ready Architecture Trade-offs

*   **Managed Services vs. Self-Hosted:**
    *   *Trade-off:* We recommend Managed Kafka and Cloud SQL over self-hosting them on Kubernetes. While this increases OPEX costs, it massively reduces operational burden (CAPEX/Engineering hours), ensuring automated backups, automated patching, and guaranteed HA SLAs.
*   **Synchronous Checkout vs. Async Choreography:**
    *   *Trade-off:* We retained synchronous inventory reservation over REST during checkout (before publishing to Kafka) rather than full asynchronous choreography. This ensures we never acknowledge an order we cannot fulfill, trading slightly higher latency and availability coupling for absolute data consistency and avoiding complex compensating "out of stock" emails.
*   **Single DB Server vs. Micro-Databases:**
    *   *Trade-off:* The PoC shares one Postgres server. In production, we evaluate moving to separate Cloud SQL instances per bounded context. This maximizes blast-radius isolation but increases baseline infrastructure costs and complicates cross-domain operational reporting.