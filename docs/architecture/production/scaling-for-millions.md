# Scaling for Millions

> **CRITICAL ARCHITECTURAL WARNING**
>
> **THIS DOCUMENT DESCRIBES A THEORETICAL SCALING STRATEGY FOR PRODUCTION.**
> **THIS IS NOT IMPLEMENTED IN THE CURRENT SINGLE-VM PROOF-OF-CONCEPT (POC).**

This document details the architectural patterns required to scale the ShopSphere Global Order Platform to handle millions of concurrent users securely and efficiently.

---

## 1. Edge Caching & Traffic Management

To survive massive traffic spikes (e.g., Black Friday sales), the platform must absorb traffic at the edge before it reaches the backend microservices.
*   **Global CDN:** Static assets (React frontend bundles, CSS, JS) and highly cacheable API responses (e.g., public catalogue images) are cached at Google Cloud CDN edge nodes.
*   **Rate Limiting:** Cloud Armor and the API Gateway enforce strict rate limits per IP address and per tenant (Keycloak Subject) to prevent scraping bots or DDoS attacks from exhausting backend resources.

## 2. Horizontal Microservice Scaling

Microservices must dynamically adjust to load.
*   **Stateless Architecture:** The `api-gateway`, `customer-service`, `catalogue-service`, and `order-service` hold zero local state. Any pod can handle any request.
*   **Horizontal Pod Autoscaling (HPA):** Configured to scale pod replicas out (up to a defined maximum) based on CPU utilization crossing 70%, or custom metrics like concurrent HTTP requests.
*   **Hotspot Mitigation:** If specific products become sudden hotspots, the system must rely on Redis caching to prevent database thread starvation.

## 3. Database Scaling & Partitioning

A single PostgreSQL writer becomes a bottleneck at enterprise scale.
*   **Read Scaling:** `catalogue-service` read queries (e.g., product searches) are offloaded to asynchronous Cloud SQL Read Replicas.
*   **Caching Tier:** Redis (Memorystore) is utilized extensively via Cache-Aside patterns. Product details and availability statuses are served from memory, drastically reducing SQL `SELECT` load.
*   **Partitioning / Sharding:** As order volume grows into the tens of millions, the `order_db` tables (e.g., `orders`, `order_items`) will require logical partitioning by date (e.g., monthly partitions) to maintain index performance.

## 4. Asynchronous Workflows & Kafka

Message brokers decouple intensive write operations to handle traffic bursts.
*   **Kafka Partitions:** The `order.created` topic is heavily partitioned (e.g., 50 partitions keyed by `customer_id`) to allow dozens of consumer pods to process events in parallel.
*   **The Outbox Pattern:** Guarantees that order commits are fast (only a local SQL insert) while the actual downstream work (email confirmations, analytics ingestion) is processed asynchronously off the main thread.
*   **Backpressure:** If downstream systems slow down, Kafka acts as a shock absorber. Consumer pods pull messages at their own pace, preventing the entire platform from collapsing.

## 5. Global Marketplaces Strategy

Scaling globally requires adapting to regional constraints.
*   **Regional Deployments:** Deploy independent instances of the ShopSphere platform in major geographic theaters (e.g., NA, EMEA, APAC) to minimize latency.
*   **Localization & Currencies:** The catalogue and order databases use `NUMERIC` types to support diverse fiat and crypto currencies seamlessly without floating-point errors.
*   **Data Residency:** Customer profiles belonging to EU citizens remain strictly within EU-hosted PostgreSQL instances to ensure GDPR compliance.
*   **Eventual Consistency:** Cross-region aggregate reporting (Executive Dashboard) relies on asynchronous Kafka replication (e.g., Confluent Cluster Linking) to build globally eventually consistent materialised views, accepting slight delays in favor of high availability.

---

## Viva-Ready Architecture Trade-offs

*   **Synchronous vs. Asynchronous Reads:**
    *   *Trade-off:* We use synchronous cache-aside for the catalogue to ensure fast reads, but we accept the risk of a "cache stampede" if Redis fails. To mitigate this, services have strict timeouts and circuit breakers that will gracefully degrade the UI if the database is overwhelmed.
*   **Strong Consistency vs. Eventual Consistency:**
    *   *Trade-off:* We enforce strong consistency (ACID transactions) inside the `order-service` bounded context to ensure we never lose an order. However, we accept *eventual consistency* across bounded contexts. For example, the `analytics-service` dashboard may lag a few seconds behind real-time because it relies on asynchronous Kafka event ingestion. This is a deliberate choice to favor scalability over global locking.