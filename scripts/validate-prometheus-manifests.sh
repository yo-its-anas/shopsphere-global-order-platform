#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly OVERLAY="${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc/prometheus"

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

main() {
  local rendered
  require_command kubectl
  rendered="$(kubectl kustomize "${OVERLAY}")"

  grep -q 'image: prom/prometheus:v3.13.1' <<<"${rendered}" ||
    fail 'The reviewed Prometheus image version is not pinned.'
  grep -q 'image: registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.19.1' <<<"${rendered}" ||
    fail 'The reviewed kube-state-metrics image version is not pinned.'
  [[ "$(grep -c 'type: ClusterIP' <<<"${rendered}")" -eq 2 ]] ||
    fail 'Prometheus and kube-state-metrics must both use ClusterIP Services.'
  ! grep -Eq 'type: (NodePort|LoadBalancer)' <<<"${rendered}" ||
    fail 'Public monitoring Service types are prohibited.'
  grep -q 'role: endpointslice' <<<"${rendered}" ||
    fail 'Kubernetes-native application discovery is required.'
  grep -q -- '--storage.tsdb.retention.time=7d' <<<"${rendered}" ||
    fail 'The bounded PoC retention period is missing.'
  grep -q 'storage: 8Gi' <<<"${rendered}" ||
    fail 'The bounded persistent storage request is missing.'
  grep -q 'runAsNonRoot: true' <<<"${rendered}" ||
    fail 'Non-root execution is required.'
  grep -q 'readOnlyRootFilesystem: true' <<<"${rendered}" ||
    fail 'A read-only root filesystem is required.'
  grep -q 'ShopSphereScrapeTargetDown' <<<"${rendered}" ||
    fail 'The core alert rules are missing.'

  printf '[OK] Prometheus manifests passed static safety and configuration validation.\n'
}

main "$@"
