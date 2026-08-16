#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly OVERLAY="${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc/wazuh"

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

  grep -q 'image: wazuh/wazuh-manager:4.14.7' <<<"${rendered}" ||
    fail 'The reviewed Wazuh Manager image version is not pinned.'
  grep -q 'image: wazuh/wazuh-agent:4.14.7' <<<"${rendered}" ||
    fail 'The reviewed Wazuh Agent image version is not pinned.'
  ! grep -Eq 'type: (NodePort|LoadBalancer)' <<<"${rendered}" ||
    fail 'Public security Service types are prohibited.'
  grep -q 'privileged: true' <<<"${rendered}" ||
    fail 'Wazuh Agent requires privileged execution to monitor the host.'

  printf '[OK] Wazuh manifests passed static safety and configuration validation.\n'
}

main "$@"
