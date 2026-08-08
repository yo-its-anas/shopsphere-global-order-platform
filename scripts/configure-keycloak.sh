#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-platform"
readonly DEPLOYMENT_NAME="keycloak"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 || fail "Required command '${command_name}' was not found."
}

main() {
    local pod_name=""

    require_command kubectl
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait \
        --for=condition=Available \
        "deployment/${DEPLOYMENT_NAME}" \
        --timeout=30s >/dev/null || fail "Keycloak Deployment is not Available."

    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod \
        -l app.kubernetes.io/name=keycloak \
        -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "No Keycloak pod was found."

    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- bash -ec '
        config=/tmp/shopsphere-kcadm-configure.config
        trap '\''rm -f "$config"'\'' EXIT
        kcadm=/opt/keycloak/bin/kcadm.sh

        "$kcadm" config credentials \
            --config "$config" \
            --server http://127.0.0.1:8080 \
            --realm master \
            --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
            --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1

        "$kcadm" update client-policies/profiles \
            -r shopsphere \
            --config "$config" \
            -f /opt/keycloak/data/configuration/client-policy-profiles.json >/dev/null

        "$kcadm" update client-policies/policies \
            -r shopsphere \
            --config "$config" \
            -f /opt/keycloak/data/configuration/client-policies.json >/dev/null
    ' >/dev/null

    printf '[OK] ShopSphere Keycloak client-policy profile and policy were reconciled.\n'
    printf '[INFO] No administrator credentials, tokens, or client secrets were displayed.\n'
}

main "$@"
