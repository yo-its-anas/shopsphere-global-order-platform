# Monitoring and Observability Platform

This directory is reserved for the ShopSphere Prometheus, Grafana, OpenTelemetry, and
Loki platform. The governing design is the
[Executive Operations and Observability Architecture](../../docs/architecture/observability-architecture.md)
and [ADR-012](../../docs/adr/ADR-012-layered-observability-source-owned-kpis.md).

## Current implementation state

The PoC OpenTelemetry Collector is implemented under
`platform/kubernetes/base/opentelemetry-collector` with a PoC overlay. It accepts
internal OTLP/gRPC and OTLP/HTTP traces, applies memory limiting and batching, emits
basic validation summaries to its own container log, and exposes internal health and
self-metrics. It does not export to an external service and is not a durable trace
backend.

Prometheus, Grafana, durable trace storage, Loki, a log collector, alert rules, and
dashboard provisioning remain outside the current deployed monitoring capability.

Existing prerequisites elsewhere in the repository are:

- UTC structured JSON logs;
- safe correlation/request IDs;
- liveness/readiness endpoints and Kubernetes probes;
- Kubernetes resource requests/limits;
- domain audit and transactional-outbox operational evidence.

Application `/metrics` endpoints are implemented for the five FastAPI workloads.
OpenTelemetry FastAPI/server instrumentation, bounded client spans, W3C `traceparent`
propagation, and JSON-log `trace_id`/`span_id` correlation are implemented and unit
validated. The PoC application ConfigMaps enable asynchronous OTLP/HTTP export to the
Collector's internal Kubernetes DNS name. Application probes do not call the Collector.
Centralized durable storage, dashboard queries, and alert validation remain Planned.
Live deployment, internal Service exposure, application-namespace connectivity, and
accepted application spans are recorded in the
[Collector platform validation evidence](../../docs/evidence/opentelemetry-collector-validation.md).

## Buffering, retry, and loss boundary

- Each Python process uses a bounded 512-span in-memory queue, exports at most 128 spans
  per batch every two seconds, and limits an export attempt to five seconds.
- OTLP transient failures are handled by the exporter without blocking business request
  completion. If the in-memory queue fills, new trace data may be dropped.
- The Collector memory limiter rejects telemetry before it exceeds its 512 MiB container
  limit; clients may retry retryable responses. Its batch processor holds at most a small
  in-memory working set before writing validation summaries to stdout.
- There is no persistent Collector queue or trace store. Collector/application restart,
  prolonged unavailability, full queues, or container-log rotation can lose telemetry.
  Transactional state, audit ledgers, and outboxes remain authoritative.
- No exporter has a network destination, and the Collector NetworkPolicy declares empty
  egress. This limits accidental external export, subject to the documented kind CNI
  enforcement limitation.

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
