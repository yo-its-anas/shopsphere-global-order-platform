#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly OVERLAY="${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc/loki"

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

  grep -q 'image: grafana/loki:3.1.0' <<<"${rendered}" ||
    fail 'The reviewed Loki image version is not pinned.'
  grep -q 'image: grafana/promtail:3.1.0' <<<"${rendered}" ||
    fail 'The reviewed Promtail image version is not pinned.'
  grep -q 'type: ClusterIP' <<<"${rendered}" ||
    fail 'Loki must use a ClusterIP Service.'
  ! grep -Eq 'type: (NodePort|LoadBalancer)' <<<"${rendered}" ||
    fail 'Public monitoring Service types are prohibited.'
  grep -q 'storage: 2Gi' <<<"${rendered}" ||
    fail 'The bounded persistent storage request is missing.'
  grep -q 'runAsNonRoot: true' <<<"${rendered}" ||
    fail 'Non-root execution is required for Loki.'
  grep -q 'readOnlyRootFilesystem: true' <<<"${rendered}" ||
    fail 'A read-only root filesystem is required.'
  grep -q 'retention_period: 48h' <<<"${rendered}" ||
    fail 'The conservative PoC retention period (48h) is missing.'

  printf '[OK] Loki manifests passed static safety and configuration validation.\n'
}

main "$@"
