#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly OVERLAY="${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc/opentelemetry-collector"
readonly COLLECTOR_DNS="opentelemetry-collector.shopsphere-monitoring.svc.cluster.local"

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

render_overlay() {
  kubectl kustomize "${OVERLAY}"
}

validate_collector() {
  local rendered
  rendered="$(render_overlay)"

  grep -q 'image: otel/opentelemetry-collector-k8s:0.158.0' <<<"${rendered}" ||
    fail "Collector image must use the reviewed pinned release."
  grep -q 'type: ClusterIP' <<<"${rendered}" ||
    fail "Collector Service must be ClusterIP."
  ! grep -Eq 'type: (NodePort|LoadBalancer)' <<<"${rendered}" ||
    fail "Public Collector Service types are prohibited."
  for port in 4317 4318 13133 8888; do
    grep -q "port: ${port}" <<<"${rendered}" ||
      fail "Expected internal Collector port ${port} is missing."
  done
  grep -q 'memory_limiter' <<<"${rendered}" ||
    fail "Memory limiter is required."
  grep -q 'readOnlyRootFilesystem: true' <<<"${rendered}" ||
    fail "Read-only root filesystem is required."
  grep -q 'runAsNonRoot: true' <<<"${rendered}" ||
    fail "Non-root execution is required."
  grep -q 'egress: \[\]' <<<"${rendered}" ||
    fail "Collector NetworkPolicy must declare no egress."
}

validate_application_configuration() {
  local component rendered
  for component in api-gateway customer-service catalogue-service order-service; do
    rendered="$(kubectl kustomize "${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc/${component}")"
    grep -q 'TELEMETRY_ENABLED' <<<"${rendered}" ||
      fail "${component} does not enable telemetry."
    grep -q "${COLLECTOR_DNS}:4318/v1/traces" <<<"${rendered}" ||
      fail "${component} does not use the internal Collector DNS endpoint."
  done
}

main() {
  require_command kubectl
  validate_collector
  validate_application_configuration
  printf '[OK] Collector and application telemetry manifests passed static validation.\n'
}

main "$@"
