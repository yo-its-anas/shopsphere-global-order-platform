#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-data"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

main() {
    local pod_name=""
    local service_type=""
    command -v kubectl >/dev/null 2>&1 || fail "Required command 'kubectl' was not found."
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get deployment redis >/dev/null
    service_type="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service redis -o jsonpath='{.spec.type}')"
    [[ "$service_type" == "ClusterIP" ]] || fail "Redis is not ClusterIP-only."
    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l app.kubernetes.io/name=redis -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "No Redis pod was found."
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait --for=condition=Ready "pod/${pod_name}" --timeout=10s >/dev/null
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- sh -ec 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --no-auth-warning ping | grep -qx PONG'
    printf '[OK] Redis is Ready, authenticated, and ClusterIP-only. No credential was displayed.\n'
}

main "$@"
