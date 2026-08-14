#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-data"
readonly POD_NAME="postgresql-0"
readonly STATEFULSET_NAME="postgresql"
readonly SECRET_NAME="shopsphere-postgresql-credentials"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 || fail "Required command '${command_name}' was not found."
}

main() {
    local catalogue_key_state=""
    local order_key_state=""
    local databases=""

    require_command kubectl

    catalogue_key_state="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" \
        get secret "$SECRET_NAME" \
        -o go-template='{{if index .data "catalogue-password"}}present{{end}}')" || \
        fail "PostgreSQL credential Secret '${SECRET_NAME}' was not found."
    [[ "$catalogue_key_state" == "present" ]] || \
        fail "Secret '${SECRET_NAME}' does not contain the catalogue credential. Run 'make postgresql-secret' first."
    order_key_state="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" \
        get secret "$SECRET_NAME" \
        -o go-template='{{if index .data "order-password"}}present{{end}}')" || \
        fail "PostgreSQL credential Secret '${SECRET_NAME}' was not found."
    [[ "$order_key_state" == "present" ]] || \
        fail "Secret '${SECRET_NAME}' does not contain the order-service credential. Run 'make postgresql-secret' first."

    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
        "statefulset/${STATEFULSET_NAME}" --timeout=300s >/dev/null || \
        fail "PostgreSQL StatefulSet did not become Ready."

    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -- \
        /docker-entrypoint-initdb.d/init-databases.sh >/dev/null || \
        fail "Database reconciliation failed. Existing databases were not intentionally removed or recreated."

    databases="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -- \
        sh -ec 'psql --tuples-only --no-align --username "$POSTGRES_USER" --dbname postgres --command="SELECT datname || '\''|'\'' || pg_get_userbyid(datdba) FROM pg_database WHERE datname IN ('\''customer_db'\'', '\''keycloak_db'\'', '\''catalogue_db'\'', '\''order_db'\'') ORDER BY datname;"')"
    grep -Fxq 'customer_db|customer_app' <<<"$databases" || \
        fail "customer_db does not exist with the expected customer_app owner."
    grep -Fxq 'keycloak_db|keycloak_app' <<<"$databases" || \
        fail "keycloak_db does not exist with the expected keycloak_app owner."
    grep -Fxq 'catalogue_db|catalogue_app' <<<"$databases" || \
        fail "catalogue_db does not exist with the expected catalogue_app owner."
    grep -Fxq 'order_db|order_app' <<<"$databases" || \
        fail "order_db does not exist with the expected order_app owner."

    printf '[OK] PostgreSQL logical databases were reconciled idempotently.\n'
    printf '[OK] customer_db, keycloak_db, catalogue_db, and order_db retain their expected dedicated owners.\n'
    printf '[INFO] No credential or secret value was displayed.\n'
}

main "$@"
