# Prometheus Platform Validation

**Validation date:** 2026-08-14  
**Environment:** ShopSphere PoC, `kind-shopsphere-poc`  
**Evidence state:** Platform Validated

## Validated capability

- Prometheus `v3.13.1` and kube-state-metrics `v2.19.1` were deployed in
  `shopsphere-monitoring` and reached `1/1` Ready.
- Both Services are `ClusterIP` and have no external address. Prometheus is available
  only on internal port `9090`.
- The `prometheus-data` local-path PVC is Bound at 8 GiB. TSDB retention is bounded to
  seven days and 6 GB.
- `promtool check config` passed for the deployed configuration and found one rule file.
  `promtool check rules` passed with five rules.
- Nine expected targets were UP: Prometheus, OpenTelemetry Collector,
  kube-state-metrics, kubelet node metrics, cAdvisor, API Gateway, Customer, Catalogue,
  and Order.
- Analytics is included in the EndpointSlice discovery allow-list but was not expected
  as a target because no analytics Kubernetes Service is deployed.
- Five safe requests were sent to API Gateway. The subsequently scraped cumulative
  request counter increased from `265` to `273`; concurrent probe or user traffic can
  account for the three additional increments.
- No alert was firing at final validation time.

## Corrective validation

The initial rollout exposed two configuration defects rather than hiding them:

1. Prometheus rejected an explicit `false` value for the default-disabled lifecycle
   flag. The unnecessary argument was removed.
2. kube-state-metrics health probes initially used the wrong port/path combination.
   They were aligned with its contract: startup `/healthz` and liveness `/livez` on the
   main port, readiness `/readyz` on the telemetry port.

The replacement kube-state-metrics pod remained Ready with zero restarts across multiple
probe intervals, and the complete target/rule check passed again.

## Evidence boundaries

The PVC is local to the only kind node. It is persistent across ordinary pod replacement,
but not replicated or backed up and does not survive loss of the VM/node/local-path
volume. Prometheus and the monitored workloads share the same failure domain.

The active alert rules cover target loss, sustained HTTP 5xx ratio, sustained p95
latency, repeated container restarts, and unavailable Deployment replicas. Inventory
low/out-of-stock alerts are not active because no authoritative aggregate business gauge
currently exists. No alert delivery route or Alertmanager was validated.
