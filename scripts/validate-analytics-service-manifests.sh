#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly OVERLAY="${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc/analytics-service"

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

  grep -q 'image: shopsphere/analytics-service:poc' <<<"${rendered}" ||
    fail 'The reviewed Analytics Service image version is not pinned.'
  grep -q 'type: ClusterIP' <<<"${rendered}" ||
    fail 'Analytics Service must use a ClusterIP Service.'
  grep -q 'runAsNonRoot: true' <<<"${rendered}" ||
    fail 'Non-root execution is required.'
  grep -q 'readOnlyRootFilesystem: true' <<<"${rendered}" ||
    fail 'A read-only root filesystem is required.'

  printf '[OK] Analytics Service manifests passed non-destructive validation.\n'
}

main "$@"
