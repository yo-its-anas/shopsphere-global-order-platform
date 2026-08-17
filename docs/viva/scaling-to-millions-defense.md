# Viva Redesign Defense: Scaling for Millions

This document provides a highly structured, technically rigorous, and assessor-ready defense script for the classic Viva scenario question: 

> *"How would you redesign ShopSphere to support millions of concurrent users across international marketplaces?"*

---

## 1. The 90-Second Executive Pitch

"To redesign ShopSphere for millions of concurrent users internationally, we transition from our virtualized single-node Proof-of-Concept into a globally distributed, zero-trust cloud-native platform on Google Cloud. 

We absorb up to $90\%$ of traffic at the edge using **Cloud DNS, Cloud CDN, and Cloud Armor WAF**, before routing clean requests via **Global External Load Balancers** to regional, multi-zone **Google Kubernetes Engine (GKE)** compute clusters. Core FastAPI microservices scale horizontally using metrics-driven **Horizontal Pod Autoscalers (HPAs)**.

We eliminate state-tier bottlenecks by offloading PostgreSQL databases to **Managed Google Cloud SQL** configured with Multi-AZ synchronous replication, utilizing **Read Replicas** for catalogue searches and **Redis (Memorystore) Cache-Aside** to mitigate database hotspots. Write operations are decoupled asynchronously using a **replicated, multi-broker Kafka** event stream backed by our transactional outbox pattern. 

To satisfy international compliance, we deploy regional localized databases, ensuring **data residency (GDPR/APEC)** while aggregating business KPIs asynchronously to build globally eventually consistent executive dashboards. Disaster recovery is secured via an Active-Passive regional warm standby, guaranteeing a defendable **5-minute RPO and 2-hour RTO**."

---

## 2. The 5-Minute Architectural Deep-Dive

### 2.1 The Edge & Traffic Ingestion Tier
*   **Recommendation:** Deploy Google Cloud DNS, Cloud CDN, Cloud Armor, and Global External HTTP(S) Load Balancing.
*   **Why:** Cloud DNS routes global traffic to the nearest regional GKE ingress point via anycast. Cloud CDN caches static catalog responses and images at edge Points of Presence (PoPs), absorbing up to $90\%$ of read traffic. Cloud Armor acts as a Web Application Firewall (WAF) to enforce rate limiting and block SQLi or DDoS attempts.
*   **Trade-off:** *Caching Freshness vs Latency.* We trade instantaneous database freshness for microsecond latency. Catalog updates are eventually consistent, requiring a strict Cache-Control invalidation strategy.
*   **When necessary:** Mandatory when daily active users (DAU) exceed $10,000$ or under immediate threat of automated scraping or brute-force attacks.

### 2.2 The Compute & Kubernetes Tier
*   **Recommendation:** Regional GKE Autopilot clusters, dedicated Node Pools, and Horizontal Pod Autoscalers (HPA).
*   **Why:** Distributes our stateless commerce engines (`customer`, `catalogue`, `order`, `api-gateway`) across three physical Availability Zones (AZs). HPAs scale pod replicas dynamically based on HTTP request rates, while the Cluster Autoscaler scales the underlying VM nodes when pods are pending. `topologySpreadConstraints` prevent all replicas from scheduling on a single failing node.
*   **Trade-off:** *Elasticity vs Resource Overhead.* We trade higher base compute costs (running nodes in multiple zones) for immediate, hands-free auto-scaling and resilience to complete zone outages.
*   **When necessary:** Necessary when traffic patterns fluctuate wildly or when high-availability SLAs demand $99.99\%$ uptime.

### 2.3 The Microservices Tier
*   **Recommendation:** Stateless FastAPI engines, Kong/GKE Ingress, and mTLS Service Mesh (Istio).
*   **Why:** Keeping services entirely stateless ensures any pod replica can process any request. Inter-service HTTP calls use connection pooling, circuit breaking, and exponential backoff retries to prevent cascading failure if a service stalls. An Istio service mesh enforces secure mTLS encryption between pods.
*   **Trade-off:** *Decoupled Complexity vs Network Overhead.* Splitting services introduces minor inter-container network latencies, which we mitigate using connection multiplexing.
*   **When necessary:** Required once development teams scale beyond $15$ engineers, requiring distinct CI/CD release boundaries.

### 2.4 The Database Tier
*   **Recommendation:** Managed Google Cloud SQL (PostgreSQL), Read Replicas, and Connection Pooling.
*   **Why:** Database writes are routed to a high-availability Primary database with synchronous replication to a standby node in another zone. All catalog-search read traffic is offloaded to asynchronous, read-only SQL replicas. Connection pools (PgBouncer) prevent Postgres process starvation under high replica scaling.
*   **Trade-off:** *Strong Consistency vs Scalability.* We maintain strict ACID consistency on the write database, but accept *eventual consistency* on read replicas, meaning a price change may take up to $5$ seconds to reflect globally.
*   **When necessary:** Mandatory when database write transactions cross $1,000$ per second or when read queries choke the Primary instance.

### 2.5 The Caching Tier
*   **Recommendation:** Managed HA Redis Cluster (Google Cloud Memorystore).
*   **Why:** Implements the cache-aside pattern. Serves product lookups and stock availability directly from in-memory shards, preventing database hotspots from reaching PostgreSQL.
*   **Trade-off:** *Memory Cost vs Database Protection.* We pay premium costs for high-capacity RAM to protect our database disks from collapsing under flash-sale spikes.
*   **When necessary:** Essential when the same popular products are queried hundreds of times per second.

### 2.6 The Asynchronous Messaging Tier
*   **Recommendation:** Managed Multi-Broker Kafka Cluster (Confluent Cloud), 50+ Partitions, and Consumer Groups.
*   **Why:** Decouples intensive order fulfillment from the checkout thread. When an order is created, we write the event atomically to the Postgres outbox. A publisher pushes it asynchronously to Kafka. 50 partitions keyed by `customer_id` allow 50 parallel consumer pods to process and fulfill orders simultaneously.
*   **Trade-off:** *Asynchronous Delay vs Immediate Throughput.* We trade immediate synchronous fulfillment verification for infinite write throughput. Checkout returns a success instantly, while inventory/delivery are updated asynchronously.
*   **When necessary:** Crucial when checkout rates exceed $500$ orders per second.

### 2.7 The Identity Tier
*   **Recommendation:** Centralized, active-active Keycloak cluster or Managed Identity Platform (OAuth2/OIDC).
*   **Why:** Offloads token generation and credential storage. The active-active clustering ensures that login actions do not become a single-point-of-failure.
*   **Trade-off:** *Self-Managed IAM Cost vs Cloud Lock-In.* We choose managed IAM over self-hosted Keycloak to offload security patch administration.
*   **When necessary:** Required when handling millions of active login sessions.

### 2.8 Global Deployment & Localization
*   **Recommendation:** Regional sharded databases, currency decimals, and localized catalogs.
*   **Why:** Independent regional GKE/PostgreSQL clusters are deployed in EU, NA, and APAC. EU citizen profile data is sharded and stored strictly within EU zones to comply with **GDPR regulations**. All currencies are stored using `NUMERIC` types to prevent floating-point rounding errors.
*   **Trade-off:** *Schema Autonomy vs Global Reporting.* We trade ease of reporting (no global SQL joins) for data-residency compliance and low-latency regional checkout operations.
*   **When necessary:** Mandatory when expanding operations outside a single continent or when local data-protection laws apply.

### 2.9 Observability & Operational Governance
*   **Recommendation:** Centralized SaaS Telemetry (Datadog/Cloud Operations) and SLI/SLO Alerting.
*   **Why:** We decommission in-cluster Prometheus/Loki to prevent monitoring from competing with application resources. We establish concrete, user-centric SLOs (e.g. $99.9\%$ of checkouts must succeed within 2 seconds).
*   **Trade-off:** *Observability Budget vs SRE Visibility.* We dedicate up to $15\%$ of our infrastructure budget to monitoring, ensuring immediate diagnostic visibility under load.
*   **When necessary:** Required when downtime cost exceeds $1,000$ USD per minute.

### 2.10 Security Tier
*   **Recommendation:** Google Secret Manager, mTLS, and Cilium/Calico NetworkPolicies.
*   **Why:** Secrets are fetched at runtime via Workload Identity (no static keys). mTLS secures inter-container transit, while private VPC clusters NAT all outbound traffic.
*   **Trade-off:** *Security Rigor vs Developer Friction.* Enforcing zero-trust Cilium policies means every service port must be explicitly declared and audited, slightly slowing initial integrations.
*   **When necessary:** Mandatory under SOC2/PCI-DSS compliance regulations.

### 2.11 Enterprise Disaster Recovery
*   **Recommendation:** Active-Passive warm standby with a 5-minute RPO and 2-hour RTO.
*   **Why:** We replicate database writes asynchronously to a secondary region. During disaster, we promote the secondary database, scale up the secondary GKE compute pool, and update Cloud DNS within 2 hours.
*   **Trade-off:** *Asynchronous DR Loss (5m RPO) vs High-Speed Transactions.* We accept a 5-minute data loss window in extreme failures to avoid the severe write latency of synchronous multi-master cross-continent replication.
*   **When necessary:** Required when business continuation SLAs demand regional failover guarantees.
