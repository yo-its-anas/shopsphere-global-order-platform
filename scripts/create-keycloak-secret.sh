#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly SOURCE_NAMESPACE="shopsphere-data"
readonly SOURCE_SECRET="shopsphere-postgresql-credentials"
readonly TARGET_NAMESPACE="shopsphere-platform"
readonly TARGET_SECRET="shopsphere-keycloak-credentials"

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

generate_password() {
    openssl rand -base64 48 | tr -d '\n'
}

generate_username() {
    printf 'kc-bootstrap-%s' "$(openssl rand -hex 8)"
}

read_password() {
    local first_value=""
    local second_value=""

    read -r -s -p 'Bootstrap administrator password: ' first_value
    printf '\n'
    read -r -s -p 'Confirm bootstrap administrator password: ' second_value
    printf '\n'

    [[ ${#first_value} -ge 20 ]] || fail "The bootstrap password must contain at least 20 characters."
    [[ "$first_value" == "$second_value" ]] || fail "Password confirmation did not match."
    printf '%s' "$first_value"
}

encode() {
    printf '%s' "$1" | base64 | tr -d '\n'
}

main() {
    local mode="${1:-interactive}"
    local database_password_base64=""
    local admin_username=""
    local admin_password=""

    [[ "$mode" == "interactive" || "$mode" == "--generate" ]] || fail "Usage: $0 [--generate]"
    require_command kubectl
    require_command base64

    kubectl --context "$KUBE_CONTEXT" get namespace "$TARGET_NAMESPACE" >/dev/null 2>&1 || \
        fail "Namespace '${TARGET_NAMESPACE}' does not exist in context '${KUBE_CONTEXT}'."

    if kubectl --context "$KUBE_CONTEXT" -n "$TARGET_NAMESPACE" get secret "$TARGET_SECRET" >/dev/null 2>&1; then
        info "Secret '${TARGET_SECRET}' already exists; it was preserved without changes."
        return
    fi

    database_password_base64="$(kubectl --context "$KUBE_CONTEXT" -n "$SOURCE_NAMESPACE" \
        get secret "$SOURCE_SECRET" -o jsonpath='{.data.keycloak-password}')"
    [[ -n "$database_password_base64" ]] || fail "The existing PostgreSQL Secret does not contain key 'keycloak-password'."

    if [[ "$mode" == "--generate" ]]; then
        require_command openssl
        admin_username="$(generate_username)"
        admin_password="$(generate_password)"
    else
        [[ -t 0 ]] || fail "Interactive credential entry requires a terminal. Use --generate only when automatic generation is explicitly intended."
        read -r -p 'Bootstrap administrator username: ' admin_username
        [[ "$admin_username" =~ ^[A-Za-z0-9._-]{8,64}$ ]] || \
            fail "The administrator username must contain 8-64 safe characters."
        admin_password="$(read_password)"
    fi

    printf '{"apiVersion":"v1","kind":"Secret","metadata":{"name":"%s","namespace":"%s"},"type":"Opaque","data":{"keycloak-db-password":"%s","bootstrap-admin-username":"%s","bootstrap-admin-password":"%s"}}' \
        "$TARGET_SECRET" \
        "$TARGET_NAMESPACE" \
        "$database_password_base64" \
        "$(encode "$admin_username")" \
        "$(encode "$admin_password")" | \
        kubectl --context "$KUBE_CONTEXT" create -f - >/dev/null

    unset database_password_base64 admin_username admin_password
    info "Secret '${TARGET_SECRET}' was created in namespace '${TARGET_NAMESPACE}'. Credential values were not displayed."
}

main "$@"
