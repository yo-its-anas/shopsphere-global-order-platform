# Monitoring and Observability Platform

This directory is reserved for the ShopSphere Prometheus, Grafana, OpenTelemetry, and
Loki platform. The governing design is the
[Executive Operations and Observability Architecture](../../docs/architecture/observability-architecture.md)
and [ADR-012](../../docs/adr/ADR-012-layered-observability-source-owned-kpis.md).

## Current implementation state

No Prometheus, Grafana, OpenTelemetry Collector, trace backend, Loki, log collector,
exporter, alert rule, or dashboard provisioning resource is currently committed here.
The directory is an architecture responsibility boundary, not deployment evidence.

Existing prerequisites elsewhere in the repository are:

- UTC structured JSON logs;
- safe correlation/request IDs;
- liveness/readiness endpoints and Kubernetes probes;
- Kubernetes resource requests/limits;
- domain audit and transactional-outbox operational evidence.

Application `/metrics` endpoints are implemented for the five FastAPI workloads. W3C
trace propagation, service/environment/trace log fields, centralized collection,
dashboard queries, and alert validation remain Planned.

## Intended contents

When implemented, keep deployable resources separated by responsibility:

- Prometheus configuration, Kubernetes discovery, recording/alert rules, and bounded
  retention;
- Grafana data sources and provisioned dashboards for Service Overview, API Performance,
  Order Processing, and Kubernetes/Platform Health;
- OpenTelemetry Collector receivers, processors, sampling, batching, and exporters;
- Loki and node-level log collection with bounded index labels;
- exporters for Kubernetes/node, PostgreSQL, Redis, and Kafka where justified;
- alert routing and runbooks without embedded receiver credentials;
- Kustomize resources/overlays with requests, limits, probes, persistent storage, and
  internal-only Services.

Generated data, credentials, local Grafana databases, Prometheus TSDB blocks, Loki
chunks, and trace data must not be committed.

## Security and cardinality rules

- Keep metrics, OTLP, Loki, and Grafana administration internal; do not create public
  NodePort or LoadBalancer services for administrative testing.
- Store runtime credentials in Kubernetes Secrets or an approved external secret manager.
- Never place customer IDs, order IDs, product IDs, JWT subjects, emails, correlation
  IDs, raw routes, tokens, or secrets in Prometheus/Loki labels.
- Never collect authorization headers, cookies, refresh tokens, passwords, database
  credentials, Keycloak secrets, or unreviewed request bodies.
- Use route templates and allow-listed service/environment/status labels.
- Treat missing telemetry as unknown, not healthy or zero.

## PoC resource and availability boundary

The monitoring stack would share one 32 GB GCP VM and one kind node with every ShopSphere
workload. Requests, limits, short retention, sampling, and cardinality budgets are
mandatory. Multiple monitoring pods on that node do not provide host-level high
availability. Total VM failure can remove both workloads and local monitoring, so an
external heartbeat is required to detect complete host loss independently.

## Required validation before claiming implementation

- rendered Kubernetes/Kustomize manifests validate;
- all monitoring Services are internal;
- pods and PVCs are Ready/Bound;
- every intended scrape target is `up` or explicitly excluded;
- synthetic metrics/logs/traces can be correlated without sensitive fields;
- Grafana dashboards load provisioned queries;
- alert rules are unit-tested and a safe synthetic alert follows its intended route;
- retention/capacity and restart behavior are observed;
- evidence distinguishes passed, failed, and not executed checks.

Production evolution requires multi-zone GKE, dedicated collectors, managed/external
metrics, durable object-backed logs/traces, resilient alert routing, long-term retention,
SLOs/SLIs, autoscaling signals, and observability outside the application failure domain.
