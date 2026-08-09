#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-data"
readonly SECRET_NAME="shopsphere-postgresql-credentials"

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

read_password() {
    local prompt="$1"
    local destination="$2"
    local first_value=""
    local second_value=""

    read -r -s -p "$prompt: " first_value
    printf '\n'
    read -r -s -p "Confirm ${prompt}: " second_value
    printf '\n'

    [[ ${#first_value} -ge 20 ]] || fail "Passwords must contain at least 20 characters."
    [[ "$first_value" == "$second_value" ]] || fail "Password confirmation did not match."
    printf -v "$destination" '%s' "$first_value"
}

encode() {
    printf '%s' "$1" | base64 | tr -d '\n'
}

main() {
    local mode="${1:-interactive}"
    local postgres_password=""
    local customer_password=""
    local keycloak_password=""

    [[ "$mode" == "interactive" || "$mode" == "--generate" ]] || fail "Usage: $0 [--generate]"
    require_command kubectl
    require_command base64

    kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" >/dev/null 2>&1 || \
        fail "Namespace '${NAMESPACE}' does not exist in context '${KUBE_CONTEXT}'."

    if kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get secret "$SECRET_NAME" >/dev/null 2>&1; then
        info "Secret '${SECRET_NAME}' already exists; it was preserved without changes."
        return
    fi

    if [[ "$mode" == "--generate" ]]; then
        require_command openssl
        postgres_password="$(generate_password)"
        customer_password="$(generate_password)"
        keycloak_password="$(generate_password)"
    else
        [[ -t 0 ]] || fail "Interactive password entry requires a terminal. Use --generate only when automatic generation is explicitly intended."
        read_password "PostgreSQL administrator password" postgres_password
        read_password "customer-service database password" customer_password
        read_password "Keycloak database password" keycloak_password
    fi

    printf '{"apiVersion":"v1","kind":"Secret","metadata":{"name":"%s","namespace":"%s"},"type":"Opaque","data":{"postgres-password":"%s","customer-password":"%s","keycloak-password":"%s"}}' \
        "$SECRET_NAME" \
        "$NAMESPACE" \
        "$(encode "$postgres_password")" \
        "$(encode "$customer_password")" \
        "$(encode "$keycloak_password")" | \
        kubectl --context "$KUBE_CONTEXT" create -f - >/dev/null

    unset postgres_password customer_password keycloak_password
    info "Secret '${SECRET_NAME}' was created in namespace '${NAMESPACE}'. Credential values were not displayed."
}

main "$@"
