#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-data"
readonly SERVICE_NAME="postgresql"
readonly STATEFULSET_NAME="postgresql"
readonly POD_NAME="postgresql-0"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 || fail "Required command '${command_name}' was not found."
}

main() {
    local service_type=""
    local cluster_ip=""
    local pvc_phase=""
    local databases=""

    require_command kubectl

    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait \
        --for=jsonpath='{.status.readyReplicas}'=1 \
        "statefulset/${STATEFULSET_NAME}" \
        --timeout=10s >/dev/null || fail "PostgreSQL StatefulSet is not Ready."

    service_type="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o jsonpath='{.spec.type}')"
    cluster_ip="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o jsonpath='{.spec.clusterIP}')"
    [[ "$service_type" == "ClusterIP" ]] || fail "PostgreSQL Service type is '${service_type}', expected ClusterIP."
    [[ -n "$cluster_ip" && "$cluster_ip" != "None" ]] || fail "PostgreSQL Service does not have an internal ClusterIP."

    pvc_phase="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc postgresql-data-postgresql-0 -o jsonpath='{.status.phase}')"
    [[ "$pvc_phase" == "Bound" ]] || fail "PostgreSQL PVC phase is '${pvc_phase}', expected Bound."

    databases="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -- \
        sh -ec 'psql --tuples-only --no-align --username "$POSTGRES_USER" --dbname postgres --command="SELECT datname || '\''|'\'' || pg_get_userbyid(datdba) FROM pg_database WHERE datname IN ('\''customer_db'\'', '\''keycloak_db'\'', '\''catalogue_db'\'', '\''order_db'\'') ORDER BY datname;"')"

    grep -Fxq 'customer_db|customer_app' <<<"$databases" || \
        fail "Logical database 'customer_db' with owner 'customer_app' was not found."
    grep -Fxq 'keycloak_db|keycloak_app' <<<"$databases" || \
        fail "Logical database 'keycloak_db' with owner 'keycloak_app' was not found."
    grep -Fxq 'catalogue_db|catalogue_app' <<<"$databases" || \
        fail "Logical database 'catalogue_db' with owner 'catalogue_app' was not found."
    grep -Fxq 'order_db|order_app' <<<"$databases" || \
        fail "Logical database 'order_db' with owner 'order_app' was not found."

    printf '[OK] StatefulSet is Ready.\n'
    printf '[OK] Service is ClusterIP-only at %s.\n' "$cluster_ip"
    printf '[OK] PVC postgresql-data-postgresql-0 is Bound.\n'
    printf '[OK] Required logical databases and distinct owners exist: customer_db/customer_app, keycloak_db/keycloak_app, catalogue_db/catalogue_app, order_db/order_app.\n'
    printf '[INFO] No credentials or secret values were read or displayed.\n'
}

main "$@"
