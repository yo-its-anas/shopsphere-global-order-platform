# OpenTelemetry Collector Platform Validation

**Validation date:** 2026-08-14  
**Environment:** ShopSphere PoC, `kind-shopsphere-poc`  
**Evidence state:** Platform Validated

## Validated scope

- The Collector and application Kustomize overlays rendered successfully and passed
  Kubernetes server-side dry-run validation.
- `opentelemetry-collector` reached `1/1` Ready with zero observed restarts in the
  `shopsphere-monitoring` namespace.
- Its Service was verified as `ClusterIP` with no external address. Internal ports are
  OTLP/gRPC `4317`, OTLP/HTTP `4318`, health `13133`, and self-metrics `8888`.
- A workload in `shopsphere-apps` resolved the Collector Kubernetes DNS name and opened
  connections to both OTLP receiver ports.
- API Gateway, Customer, Catalogue, and Order deployments were `1/1` Ready after their
  Collector endpoint configuration was applied.
- Collector self-metrics reported accepted spans. During a controlled check, the
  cumulative accepted-span count remained `431` while idle, a safe API request returned
  HTTP `200`, and the count advanced to `432`.
- Collector logs emitted basic trace summaries. No external trace exporter or SaaS
  destination is configured.

## Safety and resilience observations

Application liveness and readiness probes continue to call only the applications' own
health endpoints. Trace export is asynchronous and bounded; it is not a business-request
dependency. Collector unavailability can therefore cause telemetry loss but must not
make application liveness fail or corrupt transactional data.

The Collector uses an in-memory batch processor and memory limiter. There is no durable
queue or trace store, so restart, prolonged outage, queue pressure, or log rotation may
drop telemetry. The Collector NetworkPolicy declares no egress. NetworkPolicy enforcement
still depends on the kind cluster's CNI.

## Commands and results

| Check | Result |
| --- | --- |
| `make validate-opentelemetry-collector` | Passed |
| Kubernetes server-side dry run for the Collector and four application overlays | Passed |
| `make apply-opentelemetry-collector` and rollout wait | Passed |
| Rebuild/load/restart of four instrumented application images | Passed |
| `make otel-collector-status` | Passed |
| Focused API Gateway telemetry tests | 4 passed |
| Ruff validation for the telemetry health-exclusion change | Passed |

Prometheus, Grafana, Loki, durable trace storage, alert routing, and long-term retention
were not validated by this activity and remain Pending / Not Verified.
