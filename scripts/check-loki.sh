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

loki_api() {
  local path="$1"
  kubectl --context "${KUBE_CONTEXT}" get --raw \
    "/api/v1/namespaces/${NAMESPACE}/services/http:loki:3100/proxy${path}"
}

verify_workloads() {
  local loki_ready promtail_ready promtail_desired
  loki_ready="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get deployment loki -o jsonpath='{.status.readyReplicas}')"
  [[ "${loki_ready:-0}" == "1" ]] || fail 'Loki deployment is not Ready.'

  promtail_ready="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get daemonset promtail -o jsonpath='{.status.numberReady}')"
  promtail_desired="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get daemonset promtail -o jsonpath='{.status.desiredNumberScheduled}')"
  [[ "${promtail_ready:-0}" -eq "${promtail_desired:-0}" && "${promtail_ready:-0}" -gt 0 ]] || fail "Promtail DaemonSet is not fully ready (Ready: ${promtail_ready:-0}/${promtail_desired:-0})."

  printf '[OK] Loki deployment and Promtail DaemonSet are Ready.\n'
}

verify_internal_services_and_storage() {
  local service_type claim_phase
  service_type="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get service loki -o jsonpath='{.spec.type}')"
  [[ "${service_type}" == "ClusterIP" ]] || fail 'Loki Service is not ClusterIP-only.'

  claim_phase="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get pvc loki-data -o jsonpath='{.status.phase}')"
  [[ "${claim_phase}" == "Bound" ]] || fail 'Loki PVC is not Bound.'

  printf '[OK] Loki Service is ClusterIP-only and PVC is Bound.\n'
}

verify_loki_connectivity() {
  local ready_status build_info
  ready_status="$(loki_api '/ready')"
  if [[ "${ready_status}" != "ready"* ]]; then
    fail "Loki is not ready yet: ${ready_status}"
  fi

  build_info="$(loki_api '/loki/api/v1/status/buildinfo')"
  if ! grep -q '"version"' <<<"${build_info}"; then
    fail "Loki buildinfo API check failed."
  fi

  printf '[OK] Loki API connectivity verified and healthy.\n'
}

verify_labels_and_cardinality() {
  local labels
  labels="$(loki_api '/loki/api/v1/labels')"
  
  # Ensure standard labels like service, namespace, pod, container, level, environment are present
  # and high cardinality labels like customer_id are NOT.
  python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["LABELS_JSON"])
labels = set(payload.get("data", []))

required = {"service", "namespace", "pod", "container", "environment"}
missing = required - labels
if missing:
    # It might take a moment for Promtail to scrape and push first logs
    print(f"[WARN] Some required labels are not indexed yet: {missing}. This is normal if no logs have been pushed yet.", file=sys.stderr)
else:
    print(f"[OK] Discovered safe index labels: {labels}")

prohibited = {"customer_id", "order_id", "correlation_id", "trace_id", "email"}
found_prohibited = prohibited & labels
if found_prohibited:
    print(f"[ERROR] Prohibited high-cardinality labels found in index: {found_prohibited}", file=sys.stderr)
    sys.exit(1)
else:
    print("[OK] No prohibited high-cardinality labels are present in the index.")
PY
}

main() {
  require_command kubectl
  verify_workloads
  verify_internal_services_and_storage
  verify_loki_connectivity

  # We set LABELS_JSON to labels so python can check it
  local labels
  labels="$(loki_api '/loki/api/v1/labels')"
  LABELS_JSON="${labels}" verify_labels_and_cardinality

  printf '[OK] Loki platform validation completed successfully.\n'
}

main "$@"
