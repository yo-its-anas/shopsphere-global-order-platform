# ShopSphere Centralized Logging with Loki (PoC & Production Evolution)

This document records the design, implementation, and future production evolution of the centralized logging system implemented for the ShopSphere Enterprise Platform.

## 1. PoC Architecture Overview

The PoC centralized logging stack is deployed inside the `shopsphere-monitoring` namespace. It follows a highly resource-conscious, single-node architecture designed to fit within the strict resource quotas of our single GCP VM / kind cluster topology.

```
+-----------------------------------------------------------------+
|                       Kubernetes Cluster                        |
|                                                                 |
|  +------------------------+          +-----------------------+  |
|  |    shopsphere-apps     |          | shopsphere-monitoring |  |
|  |                        |          |                       |  |
|  |  [ api-gateway ]       |          |      +---------+      |  |
|  |  [ customer-service ] -|----------|--->  |  Loki   |      |  |
|  |  [ catalogue-service ] |  Logs    |      | (single |      |  |
|  |  [ order-service ]     |  Push    |      | replica)| <----+  |
|  +------------------------+          |      +---------+      |  |
|               |                      |           ^           |  |
|               | Write                |           | Push      |  |
|               v                      |           |           |  |
|        /var/log/pods/                |      +---------+      |  |
|               |                      |      |Promtail |      |  |
|               +----------------------|----> |(Daemon- |      |  |
|                      Read (HostPath) |      |   Set)  |      |  |
|                                      |      +---------+      |  |
|                                      +-----------------------+  |
+-----------------------------------------------------------------+
```

### 1.1 Components & Resource Constraints
- **Loki Server:** Deployed as a single monolithic replica (`Deployment`) with a local-path `2Gi` PersistentVolumeClaim for restart survival.
  - **Requests:** CPU: `25m` (0.025 Cores), Memory: `128Mi`
  - **Limits:** CPU: `75m` (0.075 Cores), Memory: `256Mi`
  - **Health Probes:** Liveness, readiness, and startup probes are fully configured using Loki's `/ready` HTTP endpoint.
- **Promtail Agent:** Deployed as a `DaemonSet` on the kind control-plane node to capture container logs under `/var/log/pods`.
  - **Requests:** CPU: `25m` (0.025 Cores) — aligned exactly with the namespace's `LimitRange` minimum.
  - **Limits:** CPU: `50m` (0.05 Cores), Memory: `128Mi`
  - **Health Probes:** Liveness and readiness are verified using Promtail's local `/ready` port `9080` endpoint.

### 1.2 Bounded Index Labels & Cardinality
Loki indexes metadata labels to find log streams quickly. High-cardinality values can corrupt Loki's index database. To avoid this, we strictly enforce the following boundaries:
- **Discovered Labels (Safe & Low-Cardinality):** `service`, `namespace`, `pod`, `container`, `environment`, `level`, and `stream`.
- **Searchable Fields (High-Cardinality — Not Indexed):** `trace_id`, `correlation_id`, `customer_id`, `order_id`, and emails remain inside the structured JSON message. These can be filtered instantly using LogQL (e.g., `{service="order-service"} |= "trace_id_value"`).

### 1.3 Conservative PoC Retention & Storage Config
- **Retention Period:** Configured to `48h` (2 days) in `limits_config.retention_period` to prevent local disk exhaustion.
- **Compactor:** Enabled and configured to run daily to execute retention policies and purge expired chunks from the local filesystem.
- **Positions File:** Saved directly in `/run/promtail/positions.yaml` mapped to `/var/run/promtail` on the host to preserve tail offsets across agent pod restarts.

---

## 2. Security & Trace Correlation

- **Secrets Sanitization:** ShopSphere microservices utilize UTC structured JSON logs and filter out sensitive payloads. No JWT tokens, Keycloak passwords, DB credentials, or Kubernetes Secret values are emitted. A security post-validation script regularly scans logs to ensure complete compliance.
- **W3C Trace Context:** The `trace_id` and `span_id` are automatically correlated in JSON log lines under the `trace_id` and `span_id` fields.
- **Request Correlation:** Incoming client requests are tagged with a unique `X-Request-ID` which maps to `correlation_id` in logs. This allows tracing a single request lifecycle as it traverses from `api-gateway` through multiple internal services.

---

## 3. Production Evolution Strategy

While a monolithic single-node Loki deployment is perfect for a professional PoC, a production-grade enterprise deployment requires transition to a highly available, durable, and secure distributed design.

```
       +-------------------------------------------------------+
       |                  Enterprise Ingestion                 |
       |                                                       |
       |     [ Promtail / OpenTelemetry Logging Exporters ]    |
       +-------------------------------------------------------+
                                   |
                                   v  (gRPC / HTTP Protobuf)
       +-------------------------------------------------------+
       |               HA Load Balancer / Gateway              |
       +-------------------------------------------------------+
            |                      |                      |
            v                      v                      v
     +--------------+       +--------------+       +--------------+
     | Loki Distrib |       | Loki Distrib |       | Loki Distrib |
     |  (Ingester)  |       |  (Querier)   |       | (Compactor)  |
     +--------------+       +--------------+       +--------------+
            \                      /                      /
             v                    v                      v
       +-------------------------------------------------------+
       |                Distributed Object Store               |
       |          (Google Cloud Storage / AWS S3)              |
       +-------------------------------------------------------+
```

### 3.1 Architecture Shift: Monolithic to Simple Scalable / Microservices
- **PoC:** Monolithic single-binary writing to local disks via PVC.
- **Production:** Deploy Loki in **Simple Scalable Mode** (separating Read and Write targets) or **Microservices Mode** (independent pods for Ingesters, Queriers, Distributors, Compactors, and Index Gateways) deployed across multiple Availability Zones to ensure zero data loss.

### 3.2 Storage Evolution: Object Storage & BoltDB/TSDB
- **PoC:** TSDB indexes and chunks stored on a local `standard` hostPath PVC volume.
- **Production:** Utilizes cloud-native, high-durability object storage:
  - **Chunks & Indexes:** Stored on GCS (Google Cloud Storage) or AWS S3.
  - **No local disks:** Nodes become stateless, utilizing local SSDs only for temporary caching (e.g., memcached or Redis) to accelerate queries.

### 3.3 HA & Ingestion Buffering
- **PoC:** Promtail sends logs directly to Loki's Single-IP service.
- **Production:** Promtail or the **OpenTelemetry Collector** exports logs to an enterprise-grade ingestion broker (e.g., **Apache Kafka** or a local **Vector** queue) before sending them to Loki. This prevents log loss during Loki maintenance windows or traffic surges.

### 3.4 Rigorous Access Control & Governance
- **Authentication:** Enable `auth_enabled: true` in Loki to support multi-tenancy.
- **Access Control:** Integrate Loki and Grafana with Keycloak / OIDC identity provider to enforce Role-Based Access Control (RBAC), ensuring developer roles can only query application-specific logs while security operators have platform-wide access.
