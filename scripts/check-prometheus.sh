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

prometheus_api() {
  local path="$1"
  kubectl --context "${KUBE_CONTEXT}" get --raw \
    "/api/v1/namespaces/${NAMESPACE}/services/http:prometheus:9090/proxy${path}"
}

verify_workloads() {
  local prometheus_ready kube_state_ready
  prometheus_ready="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get deployment prometheus -o jsonpath='{.status.readyReplicas}')"
  kube_state_ready="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get deployment kube-state-metrics -o jsonpath='{.status.readyReplicas}')"
  [[ "${prometheus_ready:-0}" == "1" ]] || fail 'Prometheus is not Ready.'
  [[ "${kube_state_ready:-0}" == "1" ]] || fail 'kube-state-metrics is not Ready.'
}

verify_internal_services_and_storage() {
  local service service_type claim_phase
  for service in prometheus kube-state-metrics; do
    service_type="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get service "${service}" -o jsonpath='{.spec.type}')"
    [[ "${service_type}" == "ClusterIP" ]] || fail "${service} is not ClusterIP-only."
  done
  claim_phase="$(kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" get pvc prometheus-data -o jsonpath='{.status.phase}')"
  [[ "${claim_phase}" == "Bound" ]] || fail 'Prometheus PVC is not Bound.'
}

verify_targets() {
  local targets analytics_present
  targets="$(prometheus_api '/api/v1/targets?state=active')"
  analytics_present='false'
  if kubectl --context "${KUBE_CONTEXT}" -n shopsphere-apps get service analytics-service >/dev/null 2>&1; then
    analytics_present='true'
  fi

  TARGETS_JSON="${targets}" ANALYTICS_PRESENT="${analytics_present}" python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["TARGETS_JSON"])
targets = payload["data"]["activeTargets"]
up = {(item["labels"].get("job"), item["labels"].get("service")) for item in targets if item["health"] == "up"}
required = {
    ("prometheus", None),
    ("opentelemetry-collector", None),
    ("kube-state-metrics", None),
    ("kubernetes-nodes", None),
    ("kubernetes-cadvisor", None),
    ("shopsphere-applications", "api-gateway"),
    ("shopsphere-applications", "customer-service"),
    ("shopsphere-applications", "catalogue-service"),
    ("shopsphere-applications", "order-service"),
}
if os.environ["ANALYTICS_PRESENT"] == "true":
    required.add(("shopsphere-applications", "analytics-service"))
missing = sorted(required - up, key=str)
if missing:
    print(f"[ERROR] Required targets are not UP: {missing}", file=sys.stderr)
    sys.exit(1)
down = [item["scrapeUrl"] for item in targets if item["health"] != "up"]
if down:
    print(f"[ERROR] Discovered targets are DOWN: {down}", file=sys.stderr)
    sys.exit(1)
print(f"[OK] {len(required)} expected scrape targets are UP.")
PY

  if [[ "${analytics_present}" == 'false' ]]; then
    printf '%s\n' '[INFO] analytics-service is discovery-ready but not deployed, so no live target was expected.'
  fi
}

verify_rules() {
  local rules
  rules="$(prometheus_api '/api/v1/rules?type=alert')"
  RULES_JSON="${rules}" python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["RULES_JSON"])
groups = payload["data"]["groups"]
rules = [rule for group in groups for rule in group.get("rules", [])]
if len(rules) != 5:
    print(f"[ERROR] Expected five alert rules, found {len(rules)}.", file=sys.stderr)
    sys.exit(1)
if any(rule.get("health") != "ok" for rule in rules):
    print("[ERROR] At least one alert rule is unhealthy.", file=sys.stderr)
    sys.exit(1)
print("[OK] Five alert rules loaded and evaluate successfully.")
PY
}

main() {
  require_command kubectl
  require_command python3
  verify_workloads
  verify_internal_services_and_storage
  verify_targets
  verify_rules
  printf '%s\n' '[OK] Prometheus is Ready, internal-only, persistent, and scraping every deployed expected target.'
}

main "$@"
