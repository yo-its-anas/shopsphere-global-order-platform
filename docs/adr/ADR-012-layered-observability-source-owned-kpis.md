# ADR-012: Use layered observability and source-owned business KPIs

## Status

Accepted and partially implemented. Structured JSON logging, correlation IDs, health
endpoints, Prometheus application metrics, OpenTelemetry FastAPI/client instrumentation,
W3C trace propagation, trace/log correlation, domain audit, and the analytics aggregation
API exist. The PoC includes one internal Collector with a memory-bounded trace pipeline
and local debug sink. Prometheus scraping, durable trace storage, central log aggregation,
Grafana dashboards, alerts, and Wazuh integration remain Planned and are not deployment
evidence.

## Context

ShopSphere must present executive business operations while also supporting application,
infrastructure, and security operations. Treating all these concerns as one dashboard or
copying transactional tables into analytics-service would blur ownership, weaken audit
integrity, and create inconsistent totals. The single-host PoC also requires strict
resource/cardinality controls and an honest availability boundary.

## Decision

Use four explicit observability boundaries:

1. Business observability uses aggregates calculated by the domain service that owns the
   transactional state.
2. Application observability uses Prometheus metrics, OpenTelemetry traces, structured
   logs, and Grafana exploration.
3. Infrastructure observability uses Kubernetes, node, and component telemetry.
4. Security observability uses Wazuh and governed identity/host sources, independently of
   service-performance monitoring.

Analytics-service will expose a read-only executive projection through API Gateway. It
will call bounded owner APIs for current PoC aggregates and may later maintain rebuildable,
idempotent Kafka-derived read models for longer history. It will not directly query or
write another service's database.

Use W3C Trace Context for distributed traces and retain `X-Request-ID` for diagnostic
correlation. Use route templates and bounded labels for metrics. Customer, order,
product, and identity identifiers never become Prometheus labels or Loki index labels.
Details are governed by the
[Executive Operations and Observability Architecture](../architecture/observability-architecture.md).

## Alternatives considered

- Direct cross-database analytics queries: fast to demonstrate but violate service data
  ownership and create schema coupling.
- Duplicate every transaction into analytics-service: supports independent queries but
  adds unnecessary consistency, privacy, replay, and storage risk for the PoC.
- Use Prometheus as the business data store: suitable for aggregate operational trends,
  not authoritative commercial history, exact money, or audit.
- Use Wazuh for all telemetry: security-focused and not a substitute for metrics, traces,
  logs, or domain KPIs.
- Put all operational information only in the React dashboard: weak for engineering
  diagnosis, alerting, retention, and role separation.

## Consequences

Business definitions remain consistent with transactional ownership, and telemetry tools
can scale/evolve independently. Analytics must handle partial failure, freshness, currency,
and eventual consistency explicitly. Instrumentation, collectors, exporters, storage,
dashboards, alert rules, runbooks, access controls, and retention add operational cost.

The React executive dashboard and Grafana serve different audiences: the former is a
governed business application; the latter is an engineering operations console.

## Security implications

Telemetry endpoints and consoles remain internal and access-controlled. Logs, metrics,
traces, and analytics responses exclude credentials, tokens, sensitive headers, and
unnecessary PII. High-cardinality identity/business values are prohibited as metric and
index labels. Wazuh file-integrity scope excludes secret and high-churn data paths.
Retention and access policies differ for application logs, traces, domain audit, Keycloak
events, and SIEM records.

## PoC limitations

The one GCP VM and one kind node would host both workloads and monitoring. A host failure
can remove the application, local telemetry, and local alerting together. Local monitoring
cannot independently confirm complete host loss. The single Collector shares that same
failure domain and has no persistent queue or trace backend. Prometheus, Grafana, Loki,
Wazuh, durable trace storage, and alert deployment are not currently implemented or
validated.

## Production evolution

Use multi-zone GKE, dedicated OpenTelemetry collectors, managed/external metrics, durable
object-backed logs and traces, multi-zone monitoring, resilient alert routing, long-term
retention, and a centralized SIEM. Define SLIs/SLOs and burn-rate alerts, use stable
autoscaling signals, protect telemetry with workload identity/mTLS where appropriate, and
operate idempotent analytics consumers with lag/reconciliation objectives. Introduce
multi-region telemetry only where recovery, latency, availability, or residency needs
justify it.

## Viva defence notes

Defend source-owned KPI calculation as protection against conflicting totals. Explain
that observability data describes system behavior but does not replace transactional or
audit truth. State that a monitoring stack colocated with the only application host is
useful for demonstration and diagnosis but is not independently resilient monitoring.
