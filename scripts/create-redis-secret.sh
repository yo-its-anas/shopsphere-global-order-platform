#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly DATA_NAMESPACE="shopsphere-data"
readonly DATA_SECRET="shopsphere-redis-credentials"
readonly APP_NAMESPACE="shopsphere-apps"
readonly APP_SECRET="shopsphere-catalogue-cache"

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

encode() {
    printf '%s' "$1" | base64 | tr -d '\n'
}

read_password() {
    local first_value=""
    local second_value=""
    read -r -s -p 'Redis password: ' first_value
    printf '\n'
    read -r -s -p 'Confirm Redis password: ' second_value
    printf '\n'
    [[ ${#first_value} -ge 24 ]] || fail "The Redis password must contain at least 24 characters."
    [[ "$first_value" == "$second_value" ]] || fail "Password confirmation did not match."
    printf '%s' "$first_value"
}

main() {
    local mode="${1:-interactive}"
    local data_exists="false"
    local app_exists="false"
    local password=""
    local encoded_password=""

    [[ "$mode" == "interactive" || "$mode" == "--generate" ]] || fail "Usage: $0 [--generate]"
    require_command kubectl
    require_command base64
    kubectl --context "$KUBE_CONTEXT" get namespace "$DATA_NAMESPACE" >/dev/null
    kubectl --context "$KUBE_CONTEXT" get namespace "$APP_NAMESPACE" >/dev/null

    kubectl --context "$KUBE_CONTEXT" -n "$DATA_NAMESPACE" get secret "$DATA_SECRET" >/dev/null 2>&1 && data_exists="true"
    kubectl --context "$KUBE_CONTEXT" -n "$APP_NAMESPACE" get secret "$APP_SECRET" >/dev/null 2>&1 && app_exists="true"
    if [[ "$data_exists" == "true" && "$app_exists" == "true" ]]; then
        info "Redis runtime Secrets already exist; both were preserved without changes."
        return
    fi
    [[ "$data_exists" == "$app_exists" ]] || fail "Only one Redis Secret exists. Reconcile the mismatch manually; no Secret was changed."

    if [[ "$mode" == "--generate" ]]; then
        require_command openssl
        password="$(openssl rand -base64 48 | tr -d '\n')"
    else
        [[ -t 0 ]] || fail "Interactive credential entry requires a terminal. Use --generate only when automatic generation is explicitly intended."
        password="$(read_password)"
    fi
    encoded_password="$(encode "$password")"
    printf '{"apiVersion":"v1","kind":"List","items":[{"apiVersion":"v1","kind":"Secret","metadata":{"name":"%s","namespace":"%s"},"type":"Opaque","data":{"redis-password":"%s"}},{"apiVersion":"v1","kind":"Secret","metadata":{"name":"%s","namespace":"%s"},"type":"Opaque","data":{"redis-password":"%s"}}]}' \
        "$DATA_SECRET" "$DATA_NAMESPACE" "$encoded_password" \
        "$APP_SECRET" "$APP_NAMESPACE" "$encoded_password" | \
        kubectl --context "$KUBE_CONTEXT" create -f - >/dev/null

    unset password encoded_password
    info "Redis runtime Secrets were created in data and application namespaces. No credential was displayed."
}

main "$@"
