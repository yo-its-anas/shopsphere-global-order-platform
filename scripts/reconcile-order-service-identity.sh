#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly KEYCLOAK_NAMESPACE="shopsphere-platform"
readonly APP_NAMESPACE="shopsphere-apps"
readonly CLIENT_ID="shopsphere-order-service"
readonly REALM_ROLE="order_service"
readonly TARGET_SECRET="shopsphere-order-service-identity"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 || \
        fail "Required command '${command_name}' was not found."
}

encode() {
    printf '%s' "$1" | base64 | tr -d '\n'
}

main() {
    local keycloak_pod=""
    local client_secret=""

    require_command kubectl
    require_command base64

    keycloak_pod="$(kubectl --context "$KUBE_CONTEXT" -n "$KEYCLOAK_NAMESPACE" get pod \
        -l app.kubernetes.io/name=keycloak \
        -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$keycloak_pod" ]] || fail "No Keycloak pod was found."
    kubectl --context "$KUBE_CONTEXT" -n "$KEYCLOAK_NAMESPACE" wait \
        --for=condition=Ready "pod/${keycloak_pod}" --timeout=30s >/dev/null

    client_secret="$(kubectl --context "$KUBE_CONTEXT" -n "$KEYCLOAK_NAMESPACE" \
        exec "$keycloak_pod" -- bash -ec '
            config=/tmp/shopsphere-order-service-identity.config
            mapper=/tmp/shopsphere-order-service-audience.json
            trap '\''rm -f "$config" "$mapper"'\'' EXIT
            kcadm=/opt/keycloak/bin/kcadm.sh
            realm=shopsphere
            client_id='"$CLIENT_ID"'
            realm_role='"$REALM_ROLE"'

            "$kcadm" config credentials --config "$config" \
                --server http://127.0.0.1:8080 --realm master \
                --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
                --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1

            if ! "$kcadm" get "roles/${realm_role}" -r "$realm" \
                --config "$config" >/dev/null 2>&1; then
                "$kcadm" create roles -r "$realm" --config "$config" \
                    -s name="$realm_role" \
                    -s description="Least-privilege inventory reservation access for order-service" \
                    -s composite=false >/dev/null
            fi

            client_doc="$("$kcadm" get clients -r "$realm" --config "$config" \
                -q clientId="$client_id" --fields id)"
            client_uuid="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' <<<"$client_doc")"
            if [[ -z "$client_uuid" ]]; then
                client_uuid="$("$kcadm" create clients -r "$realm" --config "$config" -i \
                    -s clientId="$client_id" \
                    -s name="ShopSphere Order Service" \
                    -s description="Confidential service account for inventory reservation commands" \
                    -s enabled=true -s protocol=openid-connect \
                    -s publicClient=false -s clientAuthenticatorType=client-secret \
                    -s standardFlowEnabled=false -s implicitFlowEnabled=false \
                    -s directAccessGrantsEnabled=false -s serviceAccountsEnabled=true \
                    -s fullScopeAllowed=true)"
            fi
            test -n "$client_uuid"

            "$kcadm" update "clients/${client_uuid}" -r "$realm" --config "$config" \
                -s enabled=true -s publicClient=false \
                -s standardFlowEnabled=false -s implicitFlowEnabled=false \
                -s directAccessGrantsEnabled=false -s serviceAccountsEnabled=true \
                -s fullScopeAllowed=true >/dev/null

            account_doc="$("$kcadm" get "clients/${client_uuid}/service-account-user" \
                -r "$realm" --config "$config" --fields id,username)"
            account_id="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' <<<"$account_doc")"
            account_username="$(sed -n '\''s/.*"username" : "\([^"]*\)".*/\1/p'\'' \
                <<<"$account_doc")"
            test -n "$account_id" && test -n "$account_username"
            assigned_roles="$("$kcadm" get "users/${account_id}/role-mappings/realm" \
                -r "$realm" --config "$config" --fields name)"
            if ! grep -Eq '"name"[[:space:]]*:[[:space:]]*"'"$REALM_ROLE"'"' \
                <<<"$assigned_roles"; then
                "$kcadm" add-roles -r "$realm" --config "$config" \
                    --uusername "$account_username" --rolename "$realm_role" >/dev/null
            fi

            mappers="$("$kcadm" get "clients/${client_uuid}/protocol-mappers/models" \
                -r "$realm" --config "$config" --fields name)"
            if ! grep -Eq '"name"[[:space:]]*:[[:space:]]*"shopsphere-api-audience"' \
                <<<"$mappers"; then
                printf '\''{"name":"shopsphere-api-audience","protocol":"openid-connect","protocolMapper":"oidc-audience-mapper","consentRequired":false,"config":{"included.client.audience":"shopsphere-api","access.token.claim":"true","id.token.claim":"false","introspection.token.claim":"true"}}'\'' >"$mapper"
                "$kcadm" create "clients/${client_uuid}/protocol-mappers/models" \
                    -r "$realm" --config "$config" -f "$mapper" >/dev/null
            fi

            secret_doc="$("$kcadm" get "clients/${client_uuid}/client-secret" \
                -r "$realm" --config "$config")"
            secret="$(sed -n '\''s/.*"value" : "\([^"]*\)".*/\1/p'\'' <<<"$secret_doc")"
            test -n "$secret"
            printf '\''%s'\'' "$secret"
        ')" || fail "Order-service Keycloak identity reconciliation failed."
    [[ -n "$client_secret" ]] || fail "Keycloak returned no order-service client credential."

    printf '{"apiVersion":"v1","kind":"Secret","metadata":{"name":"%s","namespace":"%s"},"type":"Opaque","data":{"client-id":"%s","client-secret":"%s"}}' \
        "$TARGET_SECRET" \
        "$APP_NAMESPACE" \
        "$(encode "$CLIENT_ID")" \
        "$(encode "$client_secret")" | \
        kubectl --context "$KUBE_CONTEXT" apply -f - >/dev/null

    unset client_secret
    printf '[OK] Keycloak order-service identity and runtime Secret were reconciled.\n'
    printf '[INFO] No administrator credential, access token, or client secret was displayed.\n'
}

main "$@"
