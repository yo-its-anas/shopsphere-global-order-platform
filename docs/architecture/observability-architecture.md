# ShopSphere Observability & Executive Operations Architecture

This document defines the complete multi-tiered observability, executive reporting, and security monitoring architecture for the ShopSphere Enterprise Platform PoC, detailing verified implementations and outlining professional production-ready recommendations.

---

## 1. Multi-Tiered Visibility Segmentation

To ensure clean operational boundaries and prevent cognitive overload, the platform strictly separates visibility into three isolated systems:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      EXECUTIVE OPERATIONS DASHBOARD                     │
│  - Purpose: Business & management KPI aggregation                       │
│  - Target Audience: Corporate executives, operations support           │
│  - Auth Model: Keycloak role checks (operations_admin / support)        │
│  - Source: analytics-service querying domain APIs & Prometheus metrics │
└────────────────────────────────────────────────┬───────────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         GRAFANA METRICS & LOGS                         │
│  - Purpose: Engineering & technical SRE troubleshooting                 │
│  - Target Audience: Site Reliability Engineers, DevOps, Developers     │
│  - Source: Prometheus (golden signals), Loki (structured streams)     │
└────────────────────────────────────────────────┬───────────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        WAZUH SECURITY SIEM                             │
│  - Purpose: Host intrusion detection, compliance, threat hunting       │
│  - Target Audience: Security Operations Center (SOC), SecOps           │
│  - Source: sandboxed File Integrity (FIM) & SCA scans inside container │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Actual Deployed State of Observability Stack

### 2.1 Prometheus (Status: Platform Validated)
*   **Deployed State:** Active single-node scraper deployed in `shopsphere-monitoring`.
*   **Target Scope:** Scrapes all microservices, API Gateway, and Kubernetes `kube-state-metrics` targets.
*   **Secure Ingress:** NetworkPolicy allows scraping of applications but strictly restricts query ingress (`9090`) to the monitoring tier and the validated `shopsphere-apps` namespace (for analytics).

### 2.2 Grafana (Status: Platform Validated)
*   **Deployed State:** Single-instance dashboard deployed in `shopsphere-monitoring`.
*   **Attributes:** Pre-configured with read-only, non-destructive datasources (Prometheus and Loki) and 4 provisioned operations dashboards for traffic, host, and database health.

### 2.3 Loki & Promtail (Status: Platform Validated)
*   **Deployed State:** Monolithic Loki server + Promtail DaemonSet in `shopsphere-monitoring`.
*   **Log Flow:** Harvests container stdout logs from `/var/log/pods` recursively.
*   **Audit Attributes:** Structured JSON logs are validated to preserve **`correlation_id`** (for end-to-end trace correlation) and **`trace_id`** mappings while shielding secrets.

### 2.4 OpenTelemetry (Status: Implemented / Backend Omitted)
*   **Deployed State:** OTEL Collector active in `shopsphere-monitoring` on ports `4317/4318`.
*   **Span Flow:** API Gateway and application FastAPI middleware correctly generate and propagate W3C trace headers.
*   **Gaps:** No trace query/visualization backend (such as Tempo) is deployed in this PoC; traces are received but cannot currently be mapped visually in Grafana.

### 2.5 Wazuh (Status: Platform Validated)
*   **Deployed State:** Sandboxed containerized Agent + Manager.
*   **SCA Policy:** Evaluates the `Amazon Linux 2023 SCA` benchmark natively (matching the agent's base image), not the host GCP VM.
*   **FIM Policy:** Integrity scans cover directories internal to the container; VM-level FIM is out of scope.

---

## 3. Single-Node PoC Limitations

The current ShopSphere platform is deployed on a **single-node GCP VM** sharing one Docker socket and one logical PostgreSQL disk.
*   **No High Availability:** Pod failure restarts improve uptime but do not provide multi-host fault isolation.
*   **Resource Contention:** Heavy traffic loads generate high disk I/O on the shared host disk, causing connection timeouts at the API Gateway level.
*   **Ephemeral Telemetry:** Metric and log storage utilize ephemeral `emptyDir` local paths, meaning database loss or container recreation deletes historical audit logs.

---

## 4. Production-Reference Recommendations

To scale ShopSphere safely to millions of concurrent enterprise users, we recommend transitioning to the following professional architecture:

### 4.1 Separate Telemetry Infrastructure
*   **Recommendation:** Move Prometheus, Grafana, Loki, and SIEM workloads completely out of the core application cluster into a dedicated, isolated "Observability Cluster" or leverage fully managed SaaS alternatives (e.g. Google Cloud Monitoring, Datadog). This ensures that heavy log aggregation doesn't choke commerce API threads.

### 4.2 Managed & Replicated Datastores
*   **Recommendation:** Utilize replicated, highly available cloud-native logging/metric backends:
    *   **Metrics:** Managed Prometheus (e.g., GCM) or Thanos/Cortex with long-term S3/GCS bucket storage.
    *   **Logs:** Highly-replicated Loki with GCS/S3 storage with a strict 90-day retention and audit-compliant archiving policy.
    *   **Traces:** Deploy **Grafana Tempo** or **Jaeger** with high-durability Cassandra/Elasticsearch persistence.

### 4.3 Scalable Collectors & Multi-Zone Ingress
*   **Recommendation:** Run OpenTelemetry Collectors in a horizontal, load-balanced deployment (`DaemonSet` agents routing to a scaled `Deployment` gateway layer). Deploy redundant, multi-zone Ingress Gateways across multiple availability zones (AZs) with global Load Balancing.

### 4.4 Centralized SIEM & Threat Intelligence
*   **Recommendation:** Migrate Wazuh from a sandboxed container into native, host-level systemd agents on every node, routing security events (syslog, auth.log, host FIM) to a high-availability Elasticsearch/OpenSearch cluster with an active threat-intelligence feed integration.

### 4.5 Service-Level Objectives (SLOs) & Alert Routing
*   **Recommendation:** Define strict, user-centric SLOs based on Golden Signals (e.g., 99.9% of catalog searches must return in < 50ms). Configure Prometheus Alertmanager to route alerts dynamically (via PagerDuty, Opsgenie, or Slack) to on-call engineering rotations with associated runbook metadata.

### 4.6 Metrics-Driven Autoscaling (HPA)
*   **Recommendation:** Implement Kubernetes Horizontal Pod Autoscaling (HPA) using custom Prometheus metrics (via `prometheus-adapter`) rather than crude CPU/Memory limits. Scale application pods automatically based on active request queue size and downstream Kafka outbox lag.
