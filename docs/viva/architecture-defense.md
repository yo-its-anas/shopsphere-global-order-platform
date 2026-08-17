# ShopSphere Architecture Defense Pack

This document serves as the formal, technically deep Architecture Defense Pack for the ShopSphere Global Enterprise Platform capstone, compiled to prepare candidates for the EduQual Level 6 Viva panel examination.

---

## Topic 1: Why a Single GCP VM?

*   **Short Answer:** Operating the PoC on a single GCP VM running a virtualized `kind` Kubernetes cluster is a deliberate decision balancing operational simplicity, resource consolidation, and extreme cost/time efficiency for an academic Proof-of-Concept, while isolating the compute topology perfectly from external network hazards.
*   **Deeper Answer:** Deploying a multi-node, multi-zone GKE cluster in the cloud during the prototyping phase introduces immense financial overhead (e.g. baseline cluster control-plane and inter-zone egress fees) and network provisioning latency. By consolidating all layers into a single high-compute GCP `n2-standard-8` (8 vCPUs, 32 GB RAM) VM, we run an identical production-ready containerized topology locally using Docker-in-Docker `kind`. All ClusterIP service definitions, YAML namespaces, and secure private NetworkPolicies remain 100% syntactically identical to a cloud-native GKE setup, enabling zero-risk cloud migrations in the future.
*   **Key Trade-off:** We traded **Hardware High Availability (HA)** for **Operational and Financial Simplicity**. The PoC cannot survive a physical GCP host hypervisor crash, but it allowed us to validate 100% of our microservices business logic, database migrations, and DevSecOps pipelines within tight educational boundaries.
*   **Common Examiner Follow-up:** *"If you are running everything on one VM, why use Kubernetes at all instead of just running Docker Compose?"*
    *   *Defensible Answer:* "Docker Compose lacks native production-grade orchestration primitives. By utilizing a single-node `kind` Kubernetes cluster, we successfully implement and validate **LimitRanges**, **ResourceQuotas**, **NetworkPolicies**, liveness/readiness probes, rolling upgrades, and declarative secrets—mechanisms that are completely unavailable or non-standard in Docker Compose."

---

## Topic 2: Platform Limitations

*   **Short Answer:** The single-node PoC has several critical physical limitations, primarily constituting a unified physical failure domain where memory, CPU, and disk storage are shared across all core applications, databases, and observability tools.
*   **Deeper Answer:** 
    *   *Database SPOF:* PostgreSQL (`postgresql-0`), Redis, and Kafka Kraft run as single-pod deployments without master-slave clustering. A single disk failure or OOMKill on the Postgres container instantly halts all database writes across all three logical databases (`customer_db`, `catalogue_db`, `order_db`).
    *   *Co-located Telemetry:* Prometheus, Grafana, and Loki are co-located in the same VM. Under high log-ingestion or metric-scraping loads, the observability stack directly competes for physical Disk I/O with the commerce database engine, inducing synthetic latency.
    *   *Virtualized SIEM:* Wazuh is deployed as a privileged DaemonSet inside the Kind container node, meaning it can only monitor container file integrity and containerized log anomalies, completely blind to the parent host VM's native SSH or hypervisor layers.
*   **Key Trade-off:** We traded **Infrastructure Blast-Radius Isolation** for **Resource Consolidation**. 
*   **Common Examiner Follow-up:** *"What is the risk of having your monitoring tools share the same host as your application databases?"*
    *   *Defensible Answer:* "It creates a shared-fate scenario. If the PostgreSQL database begins thumping the shared disk with heavy swap writes under massive concurrent load, Prometheus and Loki will experience extreme write delays, leading to metric gaps and delayed alerts at the exact moment we need monitoring data to diagnose the crisis."

---

## Topic 3: Failure & Recovery (Self-Healing)

*   **Short Answer:** ShopSphere implements a multi-tier, resilient self-healing and transaction-recovery strategy covering pod crashes, service dependency outages, database failures, and message broker drops.
*   **Deeper Answer:**
    *   *Pod & Application Failure:* Handled natively by Kubernetes ReplicaSets. If `customer-service` crashes due to an internal Python exception, the liveness probe fails, and the kubelet instantly destroys and reschedules a fresh pod.
    *   *Service Dependency Failure:* If `catalogue-service` goes offline during a checkout, the API Gateway immediately catches the connection drop and returns a clean, secure **HTTP 504 Gateway Timeout / upstream_timeout** to the client. This prevents cascading thread pool exhaustion on the gateway.
    *   *Database Outage / Kafka Outbox:* If PostgreSQL goes offline or Kafka drops network packets during order creation, the `order-service` writes the order and the `order.created` event **inside the same ACID database transaction** (Transactional Outbox Pattern). The outbox publisher daemon suspends, retrying connection with exponential backoff until Postgres/Kafka is restored, guaranteeing **at-least-once message delivery** without data loss.
*   **Key Trade-off:** We traded **Slight Latency Overhead (Transactional Outbox Polling)** for **Guaranteed Message Durability**.
*   **Common Examiner Follow-up:** *"If the order-service pod crashes midway through a database transaction, how does the system recover?"*
    *   *Defensible Answer:* "PostgreSQL's Write-Ahead Log (WAL) and ACID compliance guarantee that the transaction is completely rolled back on startup. The order is never partially written, and since the client uses a stable `Idempotency-Key` during checkout, the client can safely retry the exact same request without risk of duplicate order creation or double-allocation."

---

## Topic 4: Scaling

*   **Short Answer:** We scale the PoC vertically by provisioning high-tier GCP resources, and horizontally using Kubernetes **Horizontal Pod Autoscalers (HPA)** for stateless microservices.
*   **Deeper Answer:** 
    *   *Horizontal Scaling:* Stateless core services (`customer`, `catalogue`, `order`, `api-gateway`) run as decoupled deployments. HPAs scale pod replicas out (up to a defined limit) when CPU utilization crosses $70\%$ or when customized Prometheus HTTP request rate signals are received.
    *   *Real HA Constraints:* True high availability is constrained because all scaled pod replicas are ultimately scheduled on the **same physical GCP VM host**.
*   **Key Trade-off:** We traded **Dynamic Pod Elasticity** for **Physical Resource Constraints** on a single node.
*   **Common Examiner Follow-up:** *"If you scale order-service to 10 pods, does it make the application more highly available in your current setup?"*
    *   *Defensible Answer:* "It improves application throughput and prevents single-pod software failures from disrupting traffic. However, it does not provide true hardware high availability; because all 10 pods share the same physical GCP VM and virtual disk, a host hypervisor crash or disk failure will instantly take down all 10 replicas."

---

## Topic 5: Security Architecture

*   **Short Answer:** ShopSphere enforces a zero-trust, defense-in-depth security model spanning edge isolation, centralized Identity Provider (IDP) authentication, least-privilege RBAC, and compile-time policy-as-code gates.
*   **Deeper Answer:**
    *   *Authentication & RBAC:* Keycloak is the authoritative credential store (using secure password hashing). JWT tokens are cryptographically verified (RS256) at the API Gateway. Access control is enforced server-side based on validated token claims (`customer`, `support`, `operations_admin`), completely neutralizing IDOR attacks.
    *   *DevSecOps Gates:* Bandit and Semgrep SAST scans detect code-level security vulnerabilities. Trivy checks third-party dependencies and container images for CVEs. Open Policy Agent (OPA) evaluates manifests against `security.rego` to block privileged or root containers before deployment.
    *   *Network Security:* Custom NetworkPolicies restrict namespace egress and ingress strictly to approved pods (e.g. blocking database pods from accessing the public internet).
*   **Key Trade-off:** We traded **Developer Speed** for **Extremely Strict Quality and Security Gates**.
*   **Common Examiner Follow-up:** *"How does your API Gateway prevent a malicious user from querying another customer's order history (IDOR)?"*
    *   *Defensible Answer:* "The API Gateway and order-service never trust user-supplied customer IDs in the request body. They decode the validated RS256 Bearer JWT token, extract the unique, immutable **Keycloak subject (`sub`)**, and query the database strictly using that validated subject, neutralizing IDOR manipulation entirely."

---

## Topic 6: Transaction Reliability

*   **Short Answer:** We enforce absolute transaction reliability and stock safety using a synchronous reservation-based Saga, database-level row locks, and idempotent checkout operations.
*   **Deeper Answer:**
    *   *Stock Safety:* During checkout, the `order-service` synchronously calls `/api/v1/inventory/reserve` on the `catalogue-service`. The Catalogue service opens a database transaction, executes a `SELECT ... FOR UPDATE` row lock on the specific SKU, subtracts the requested quantity, and adds it to `reserved` (double-entry ledger).
    *   *Idempotency:* The frontend client generates a unique `Idempotency-Key` for every checkout attempt. The `order-service` stores this key in the database. If a duplicate checkout request arrives, the service blocks re-processing and immediately returns the cached confirmed order payload, preventing duplicate charges.
*   **Key Trade-off:** We traded **Availability Coupling (Synchronous catalogue call during checkout)** for **Absolute Data Consistency and Zero Overselling**.
*   **Common Examiner Follow-up:** *"What happens if the inventory reservation succeeds, but the order database write fails?"*
    *   *Defensible Answer:* "The order database transaction is rolled back completely. For the reserved catalogue stock, we implement a **Saga Compensating Event**. The outbox publisher detects the transactional abort, and an asynchronous Kafka event triggers the catalogue-service to release the reserved stock, ensuring eventual consistency across the distinct data stores."

---

## Topic 7: Observability & Diagnostics

*   **Short Answer:** Observability is structured across three distinct pillars: Executive Dashboard (business KPIs), Grafana/Loki (engineering telemetry), and Wazuh (security monitoring), avoiding single-tool overloads.
*   **Deeper Answer:**
    *   *Prometheus:* Scrapes `/metrics` endpoints asynchronously to track active request rates, error rates, and pod target states (`up`).
    *   *Loki & Promtail:* Ingests stdout JSON streams from `/var/log/pods`. Logs are structured to preserve W3C trace contexts and business correlation IDs.
    *   *OpenTelemetry:* FastAPI middleware injects traceparent headers to propagate technical spans over OTLP.
*   **Key Trade-off:** We traded **Telemetry Storage Overhead** for **Unprecedented Diagnostic Visibility**.
*   **Common Examiner Follow-up:** *"Why use both a Correlation ID and a Trace ID?"*
    *   *Defensible Answer:* "A Correlation ID is a unified business identifier assigned by the API Gateway to track a logical request across separate system logs (Loki). A Trace ID is a technical OpenTelemetry span identifier used to profile exact function-call latency, network hops, and execution bottlenecks across distributed service layers."

---

## Topic 8: Production Evolution (GKE)

*   **Short Answer:** In a live enterprise production environment, we recommend transitioning to a regional multi-zone Google Kubernetes Engine (GKE) cluster, completely externalizing all stateful tiers to Google Cloud SQL (PostgreSQL), Memorystore (Redis), and Managed Kafka (Confluent/MSK).
*   **Deeper Answer:**
    *   *Stateless Compute:* Re-deploy core services to GKE. Distribute replicas across three availability zones using `topologySpreadConstraints` and enforce minimum availability during upgrades via `PodDisruptionBudgets`.
    *   *Managed State:* Move databases to Cloud SQL configured with Multi-AZ Regional High Availability (synchronous replication with automated DNS failover) and Point-in-Time Recovery (PITR) via Write-Ahead Logs.
    *   *Managed Messaging:* Migrate Kafka to Confluent Cloud or Google Cloud Managed Kafka, setting replica factors to 3.
*   **Key Trade-off:** We trade **Higher Monthly Infrastructure OPEX** for **Absolute Data Durability, Scalability, and Automated Cloud Operations**.
*   **Common Examiner Follow-up:** *"When does managed Kubernetes (GKE) become more appropriate than your self-hosted Kind PoC?"*
    *   *Defensible Answer:* "The self-hosted Kind cluster is appropriate *only* for single-developer offline prototyping and pipeline validation. GKE becomes mandatory when the business requires **horizontal host VM scaling**, **automated cloud load-balancer provisioning**, **managed security updates**, **guaranteed zone-failure SLAs**, and zero-downtime rolling upgrades under millions of live concurrent users."

---

## Topic 9: Scaling for Millions of Users

*   **Short Answer:** Scaling to millions requires edge caching (Cloud CDN), horizontal compute auto-scaling (HPA), database read-scaling replicas, Kafka partition parallelisms, and strict API Gateway rate limiting.
*   **Deeper Answer:**
    *   *Edge Caching:* Cached public catalogue items at Google Cloud CDN edge points absorb up to $90\%$ of catalog read requests, preventing origin service starvation.
    *   *Read Scaling:* We deploy Cloud SQL read replicas in secondary regions to offload SELECT queries from the primary master database.
    *   *Kafka Parallelism:* The `order.created` topic is partitioned across 50 brokers, allowing 50 concurrent consumer pods to ingest events simultaneously.
*   **Key Trade-off:** We trade **Data Freshness (Eventual Consistency across read-replicas)** for **Extreme Read Throughput and Scalability**.
*   **Common Examiner Follow-up:** *"How do you handle 'hotspots' (e.g. thousands of users trying to buy the exact same product simultaneously)?"*
    *   *Defensible Answer:* "We protect the database by serving product details exclusively from a Redis (Memorystore) cache-aside cluster. Stock reservations are queued sequentially via database row locks, and any out-of-stock state is instantly propagated to Redis to invalidate queries at the cache layer, keeping traffic off the write database."

---

## Topic 10: Global Expansion & Disaster Recovery

*   **Short Answer:** Global expansion is achieved through regional multi-zone GKE clusters, localized fiat currencies, GDPR compliance via separate geographic databases, and a robust Active-Passive Disaster Recovery failover plan with a 5-minute RPO and 2-hour RTO.
*   **Deeper Answer:**
    *   *Data Residency:* To satisfy GDPR, EU customer profile databases are physically hosted in EU GCP zones, separated from NA/APAC states, communicated only via secure compliance-vetted transit layers.
    *   *Eventual Consistency:* Cross-region dashboard aggregates are synced asynchronously via Kafka Cluster Mirroring, ensuring high availability.
    *   *Disaster Recovery:* We maintain a standby GKE cluster in a secondary region. PostgreSQL data is replicated asynchronously. During regional failover, we promote the standby database, update cluster DNS, and scale up GKE pods to resume operations within 2 hours.
*   **Key Trade-off:** We trade **Disaster Recovery Perfection (Accepting 5-minute RPO data loss)** for **High-Performance Localized Operations (Avoiding global synchronous locks)**.
*   **Common Examiner Follow-up:** *"Why not promise zero-RPO and zero-RTO for a global enterprise?"*
    *   *Defensible Answer:* "A zero-RPO/zero-RTO SLA requires global synchronous multi-master database replication (like Google Cloud Spanner). This forces every single write transaction to wait for multi-continental network round-trip acknowledgements, adding hundreds of milliseconds of latency to every checkout. We trade absolute disaster perfection to guarantee a fast, reliable checkout experience."
