#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly SOURCE_NAMESPACE="shopsphere-data"
readonly SOURCE_SECRET="shopsphere-postgresql-credentials"
readonly TARGET_NAMESPACE="shopsphere-apps"
readonly TARGET_SECRET="shopsphere-catalogue-service-database"

info() {
    printf '[INFO] %s\n' "$*"
}

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 || fail "Required command '${command_name}' was not found."
}

main() {
    local password_base64=""
    local encoded_password=""
    local database_url=""
    local database_url_base64=""

    require_command kubectl
    require_command base64
    require_command python3

    kubectl --context "$KUBE_CONTEXT" get namespace "$TARGET_NAMESPACE" >/dev/null 2>&1 || \
        fail "Namespace '${TARGET_NAMESPACE}' does not exist in context '${KUBE_CONTEXT}'."

    if kubectl --context "$KUBE_CONTEXT" -n "$TARGET_NAMESPACE" get secret "$TARGET_SECRET" >/dev/null 2>&1; then
        info "Secret '${TARGET_SECRET}' already exists; it was preserved without changes."
        return
    fi

    password_base64="$(kubectl --context "$KUBE_CONTEXT" -n "$SOURCE_NAMESPACE" \
        get secret "$SOURCE_SECRET" -o jsonpath='{.data.catalogue-password}')" || \
        fail "The PostgreSQL credential Secret was not found."
    [[ -n "$password_base64" ]] || \
        fail "The existing PostgreSQL Secret does not contain key 'catalogue-password'."

    encoded_password="$(printf '%s' "$password_base64" | base64 --decode | \
        python3 -c 'import sys; from urllib.parse import quote; print(quote(sys.stdin.read(), safe=""), end="")')"
    [[ -n "$encoded_password" ]] || fail "The database credential could not be encoded."

    database_url="postgresql+psycopg://catalogue_app:${encoded_password}@postgresql.shopsphere-data.svc.cluster.local:5432/catalogue_db"
    database_url_base64="$(printf '%s' "$database_url" | base64 | tr -d '\n')"

    printf '{"apiVersion":"v1","kind":"Secret","metadata":{"name":"%s","namespace":"%s"},"type":"Opaque","data":{"database-url":"%s"}}' \
        "$TARGET_SECRET" \
        "$TARGET_NAMESPACE" \
        "$database_url_base64" | \
        kubectl --context "$KUBE_CONTEXT" create -f - >/dev/null

    unset password_base64 encoded_password database_url database_url_base64
    info "Secret '${TARGET_SECRET}' was created in namespace '${TARGET_NAMESPACE}'. No credential value was displayed."
}

main "$@"
