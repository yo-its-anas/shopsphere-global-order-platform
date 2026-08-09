#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-apps"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

main() {
    local pod_name=""
    local service_type=""

    command -v kubectl >/dev/null 2>&1 || fail "Required command 'kubectl' was not found."
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get deployment customer-service >/dev/null

    service_type="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" \
        get service customer-service -o jsonpath='{.spec.type}')"
    [[ "$service_type" == "ClusterIP" ]] || fail "customer-service is not ClusterIP-only."

    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods \
        -l app.kubernetes.io/name=customer-service \
        -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "No customer-service pod was found."

    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait \
        --for=condition=Ready "pod/${pod_name}" --timeout=10s >/dev/null
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- \
        python -c "import urllib.request; response=urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3); assert response.status == 200"
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- \
        python -c "import urllib.request; response=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); assert response.status == 200"

    printf '[OK] customer-service is Ready, both health endpoints return HTTP 200, and its Service is ClusterIP-only.\n'
}

main "$@"

