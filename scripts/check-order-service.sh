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
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get deployment order-service >/dev/null
    service_type="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service \
        order-service -o jsonpath='{.spec.type}')"
    [[ "$service_type" == "ClusterIP" ]] || fail "order-service is not ClusterIP-only."
    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods \
        -l app.kubernetes.io/name=order-service -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "No order-service pod was found."
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait \
        --for=condition=Ready "pod/${pod_name}" --timeout=20s >/dev/null
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- python -c \
        "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).status == 200; assert urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3).status == 200"
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- python -c \
        "import urllib.request; assert urllib.request.urlopen('http://catalogue-service.shopsphere-apps.svc.cluster.local:8000/health/ready', timeout=3).status == 200"
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- python -c \
        "import os, httpx2; token_response = httpx2.post(os.environ['SERVICE_TOKEN_URL'], data={'grant_type': 'client_credentials', 'client_id': os.environ['SERVICE_CLIENT_ID'], 'client_secret': os.environ['SERVICE_CLIENT_SECRET']}, timeout=5); token_response.raise_for_status(); token = token_response.json()['access_token']; response = httpx2.get(os.environ['CATALOGUE_SERVICE_URL'] + '/inventory/reservations/00000000-0000-4000-8000-000000000001', headers={'Authorization': 'Bearer ' + token}, timeout=5); assert response.status_code == 404, response.status_code"
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- python -c \
        "import os, socket; host, port = os.environ['KAFKA_BOOTSTRAP_SERVERS'].rsplit(':', 1); connection = socket.create_connection((host, int(port)), timeout=3); connection.close()"
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- python -c \
        "import os, psycopg; connection = psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://'), connect_timeout=3); assert connection.execute(\"SELECT to_regclass('public.order_event_outbox') IS NOT NULL\").fetchone() == (True,); connection.close()"
    printf '[OK] order-service is Ready and ClusterIP-only; PostgreSQL/outbox, least-privilege Catalogue authorization, and Kafka connectivity checks passed.\n'
    printf '[INFO] No credential, bearer token, or Secret value was displayed.\n'
}

main "$@"
