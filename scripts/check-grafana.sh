#!/usr/bin/env bash
set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-monitoring"

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

verify_workloads() {
  local grafana_ready
  grafana_ready="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get deployment grafana -o jsonpath='{.status.readyReplicas}')"
  [[ "${grafana_ready:-0}" == "1" ]] || fail 'Grafana deployment is not Ready.'

  printf '[OK] Grafana deployment is Ready.\n'
}

verify_internal_services_and_storage() {
  local service_type claim_phase
  service_type="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get service grafana -o jsonpath='{.spec.type}')"
  [[ "${service_type}" == "ClusterIP" ]] || fail 'Grafana Service is not ClusterIP-only.'

  claim_phase="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get pvc grafana-data -o jsonpath='{.status.phase}')"
  [[ "${claim_phase}" == "Bound" ]] || fail 'Grafana PVC is not Bound.'

  printf '[OK] Grafana Service is ClusterIP-only and PVC is Bound.\n'
}

verify_grafana_api() {
  local health
  # Port forward temporarily to check API health, since ClusterIP is internal
  # Another way is to use kubectl get --raw to the proxy endpoint
  health="$(kubectl --context "${KUBE_CONTEXT}" get --raw "/api/v1/namespaces/${NAMESPACE}/services/http:grafana:3000/proxy/api/health" || true)"
  
  if ! grep -q '"database": "ok"' <<<"${health}"; then
    fail "Grafana health API check failed: ${health}"
  fi
  printf '[OK] Grafana API connectivity verified and healthy.\n'
}

main() {
  require_command kubectl
  verify_workloads
  verify_internal_services_and_storage
  verify_grafana_api

  printf '[OK] Grafana platform validation completed successfully.\n'
}

main "$@"
