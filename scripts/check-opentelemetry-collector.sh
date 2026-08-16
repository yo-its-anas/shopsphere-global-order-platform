#!/usr/bin/env bash
set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly MONITORING_NAMESPACE="shopsphere-monitoring"
readonly APPLICATION_NAMESPACE="shopsphere-apps"
readonly COLLECTOR_SERVICE="opentelemetry-collector"

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

verify_workload() {
  local ready
  ready="$(kubectl --context "${KUBE_CONTEXT}" -n "${MONITORING_NAMESPACE}" get deployment "${COLLECTOR_SERVICE}" -o jsonpath='{.status.readyReplicas}')"
  [[ "${ready:-0}" == "1" ]] || fail "Collector Deployment is not Ready."
}

verify_service() {
  local service_type ports
  service_type="$(kubectl --context "${KUBE_CONTEXT}" -n "${MONITORING_NAMESPACE}" get service "${COLLECTOR_SERVICE}" -o jsonpath='{.spec.type}')"
  [[ "${service_type}" == "ClusterIP" ]] || fail "Collector Service is not ClusterIP."

  ports="$(kubectl --context "${KUBE_CONTEXT}" -n "${MONITORING_NAMESPACE}" get service "${COLLECTOR_SERVICE}" -o jsonpath='{range .spec.ports[*]}{.port}{"\n"}{end}')"
  for expected in 4317 4318 13133 8888; do
    grep -qx "${expected}" <<<"${ports}" ||
      fail "Collector Service port ${expected} is missing."
  done
}

verify_application_connectivity() {
  local pod
  pod="$(kubectl --context "${KUBE_CONTEXT}" -n "${APPLICATION_NAMESPACE}" get pod -l app.kubernetes.io/name=api-gateway -o jsonpath='{.items[0].metadata.name}')"
  [[ -n "${pod}" ]] || fail "No API Gateway pod is available for the namespace check."

  kubectl --context "${KUBE_CONTEXT}" -n "${APPLICATION_NAMESPACE}" exec "${pod}" -- python -c '
import socket
host = "opentelemetry-collector.shopsphere-monitoring.svc.cluster.local"
for port in (4317, 4318):
    with socket.create_connection((host, port), timeout=3):
        pass
' >/dev/null
}

verify_received_spans() {
  local metrics
  metrics="$(kubectl --context "${KUBE_CONTEXT}" get --raw "/api/v1/namespaces/${MONITORING_NAMESPACE}/services/http:${COLLECTOR_SERVICE}:8888/proxy/metrics")"
  awk '
    /^otelcol_receiver_accepted_spans/ && $NF + 0 > 0 { received = 1 }
    END { exit(received ? 0 : 1) }
  ' <<<"${metrics}" || fail "Collector has not reported accepting an application span."
}

main() {
  require_command kubectl
  verify_workload
  verify_service
  verify_application_connectivity
  verify_received_spans
  printf '%s\n' '[OK] Collector is Ready and ClusterIP-only; application namespace connectivity and accepted spans are verified.'
}

main "$@"
