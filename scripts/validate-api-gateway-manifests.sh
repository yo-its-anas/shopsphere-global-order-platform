#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly OVERLAY="${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc/api-gateway"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_text() {
    local content="$1"
    local expected="$2"
    grep -Fq -- "$expected" <<<"$content" || fail "Required API Gateway configuration was not found: ${expected}"
}

main() {
    local rendered=""
    command -v kubectl >/dev/null 2>&1 || fail "Required command 'kubectl' was not found."
    rendered="$(kubectl kustomize "$OVERLAY")"
    [[ -n "$rendered" ]] || fail "API Gateway overlay rendered no resources."
    grep -Eq '^kind: Secret$' <<<"$rendered" && fail "The API Gateway must not generate a committed Secret."
    grep -Eq '^[[:space:]]+type: (NodePort|LoadBalancer)$' <<<"$rendered" && fail "The API Gateway PoC Service must be ClusterIP-only."
    require_text "$rendered" "namespace: shopsphere-apps"
    require_text "$rendered" "type: ClusterIP"
    require_text "$rendered" "CUSTOMER_SERVICE_URL: http://customer-service.shopsphere-apps.svc.cluster.local:8000"
    require_text "$rendered" "CATALOGUE_SERVICE_URL: http://catalogue-service.shopsphere-apps.svc.cluster.local:8000"
    require_text "$rendered" "path: /health/ready"
    require_text "$rendered" "path: /health/live"
    require_text "$rendered" "readOnlyRootFilesystem: true"
    require_text "$rendered" "runAsNonRoot: true"
    require_text "$rendered" "kind: NetworkPolicy"
    require_text "$rendered" "type: RollingUpdate"
    printf '%s\n' "$rendered" | kubectl create --dry-run=client --validate=false -f - >/dev/null
    printf '[OK] API Gateway manifests passed non-destructive validation.\n'
}

main "$@"
