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
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get deployment api-gateway >/dev/null
    service_type="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service api-gateway -o jsonpath='{.spec.type}')"
    [[ "$service_type" == "ClusterIP" ]] || fail "api-gateway is not ClusterIP-only."
    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l app.kubernetes.io/name=api-gateway -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "No API Gateway pod was found."
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait --for=condition=Ready "pod/${pod_name}" --timeout=10s >/dev/null
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).status == 200; assert urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=6).status == 200"
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- python -c "import urllib.error, urllib.request; request = urllib.request.Request('http://127.0.0.1:8000/api/v1/products');
try:
    urllib.request.urlopen(request, timeout=6)
except urllib.error.HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError('Unauthenticated catalogue request was not rejected by the authoritative backend')"
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- python -c "import urllib.error, urllib.request; request = urllib.request.Request('http://127.0.0.1:8000/api/v1/carts/me');
try:
    urllib.request.urlopen(request, timeout=6)
except urllib.error.HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError('Unauthenticated order request was not rejected by the authoritative backend')"
    printf '[OK] API Gateway is Ready and ClusterIP-only; Catalogue and Order routes reached authoritative backend authorization and returned HTTP 401 without tokens.\n'
}

main "$@"
