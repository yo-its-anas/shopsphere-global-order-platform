#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-platform"
readonly DEPLOYMENT_NAME="keycloak"
readonly ACTIVITY_SECRET_NAMESPACE="shopsphere-apps"
readonly ACTIVITY_SECRET_NAME="shopsphere-customer-activity-keycloak"
readonly ACTIVITY_CLIENT_ID="shopsphere-customer-activity-reader"

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

main() {
    local pod_name=""
    local activity_client_secret=""

    require_command kubectl
    require_command base64
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait \
        --for=condition=Available \
        "deployment/${DEPLOYMENT_NAME}" \
        --timeout=30s >/dev/null || fail "Keycloak Deployment is not Available."

    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod \
        -l app.kubernetes.io/name=keycloak \
        -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "No Keycloak pod was found."

    activity_client_secret="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- bash -ec '
        config=/tmp/shopsphere-kcadm-configure.config
        scope_document=/tmp/shopsphere-activity-reader-scope.json
        trap '\''rm -f "$config" "$scope_document"'\'' EXIT
        kcadm=/opt/keycloak/bin/kcadm.sh
        activity_client_id=shopsphere-customer-activity-reader

        "$kcadm" config credentials \
            --config "$config" \
            --server http://127.0.0.1:8080 \
            --realm master \
            --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
            --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1

        "$kcadm" update realms/shopsphere --config "$config" \
            -s eventsEnabled=true \
            -s eventsExpiration=604800 \
            -s adminEventsEnabled=true \
            -s adminEventsDetailsEnabled=false \
            -s '\''enabledEventTypes=["LOGIN","LOGIN_ERROR","REGISTER","REGISTER_ERROR","LOGOUT","UPDATE_PASSWORD","UPDATE_PASSWORD_ERROR","SEND_RESET_PASSWORD","RESET_PASSWORD","RESET_PASSWORD_ERROR","UPDATE_PROFILE","UPDATE_PROFILE_ERROR","UPDATE_EMAIL","UPDATE_EMAIL_ERROR","CLIENT_LOGIN","CLIENT_LOGIN_ERROR","REFRESH_TOKEN","REFRESH_TOKEN_ERROR","CODE_TO_TOKEN","CODE_TO_TOKEN_ERROR"]'\'' >/dev/null

        "$kcadm" update client-policies/profiles \
            -r shopsphere \
            --config "$config" \
            -f /opt/keycloak/data/configuration/client-policy-profiles.json >/dev/null

        "$kcadm" update client-policies/policies \
            -r shopsphere \
            --config "$config" \
            -f /opt/keycloak/data/configuration/client-policies.json >/dev/null

        client_doc="$("$kcadm" get clients -r shopsphere --config "$config" \
            -q clientId="$activity_client_id" --fields id)"
        client_uuid="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' <<<"$client_doc")"
        if [[ -z "$client_uuid" ]]; then
            client_uuid="$("$kcadm" create clients -r shopsphere --config "$config" -i \
                -s clientId="$activity_client_id" \
                -s name="ShopSphere Customer Activity Reader" \
                -s description="Dedicated least-privilege service account for reading selected identity events" \
                -s enabled=true \
                -s protocol=openid-connect \
                -s publicClient=false \
                -s clientAuthenticatorType=client-secret \
                -s standardFlowEnabled=false \
                -s implicitFlowEnabled=false \
                -s directAccessGrantsEnabled=false \
                -s serviceAccountsEnabled=true \
                -s fullScopeAllowed=false)"
        fi
        test -n "$client_uuid"

        "$kcadm" update "clients/${client_uuid}" -r shopsphere --config "$config" \
            -s enabled=true \
            -s publicClient=false \
            -s standardFlowEnabled=false \
            -s implicitFlowEnabled=false \
            -s directAccessGrantsEnabled=false \
            -s serviceAccountsEnabled=true \
            -s fullScopeAllowed=false >/dev/null

        service_account_doc="$("$kcadm" get "clients/${client_uuid}/service-account-user" \
            -r shopsphere --config "$config" --fields username)"
        service_account_username="$(sed -n '\''s/.*"username" : "\([^"]*\)".*/\1/p'\'' \
            <<<"$service_account_doc")"
        test -n "$service_account_username"
        "$kcadm" add-roles -r shopsphere --config "$config" \
            --uusername "$service_account_username" \
            --cclientid realm-management \
            --rolename view-events >/dev/null

        realm_management_doc="$("$kcadm" get clients -r shopsphere --config "$config" \
            -q clientId=realm-management --fields id)"
        realm_management_uuid="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' \
            <<<"$realm_management_doc")"
        test -n "$realm_management_uuid"
        view_events_doc="$("$kcadm" get "clients/${realm_management_uuid}/roles/view-events" \
            -r shopsphere --config "$config" --fields id)"
        view_events_uuid="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' \
            <<<"$view_events_doc")"
        test -n "$view_events_uuid"
        scope_mappings="$("$kcadm" get \
            "clients/${client_uuid}/scope-mappings/clients/${realm_management_uuid}" \
            -r shopsphere --config "$config" --fields name)"
        if ! grep -Eq '\''"name"[[:space:]]*:[[:space:]]*"view-events"'\'' \
            <<<"$scope_mappings"; then
            printf '\''[{"id":"%s","name":"view-events","clientRole":true,"containerId":"%s"}]'\'' \
                "$view_events_uuid" "$realm_management_uuid" >"$scope_document"
            "$kcadm" create \
                "clients/${client_uuid}/scope-mappings/clients/${realm_management_uuid}" \
                -r shopsphere --config "$config" -f "$scope_document" >/dev/null
        fi

        secret_doc="$("$kcadm" get "clients/${client_uuid}/client-secret" \
            -r shopsphere --config "$config")"
        activity_secret="$(sed -n '\''s/.*"value" : "\([^"]*\)".*/\1/p'\'' <<<"$secret_doc")"
        test -n "$activity_secret"
        printf '\''%s'\'' "$activity_secret"
    ')"
    [[ -n "$activity_client_secret" ]] || fail "Keycloak did not return the activity-reader client credential."

    kubectl --context "$KUBE_CONTEXT" get namespace "$ACTIVITY_SECRET_NAMESPACE" >/dev/null 2>&1 || \
        fail "Namespace '${ACTIVITY_SECRET_NAMESPACE}' does not exist."
    printf '{"apiVersion":"v1","kind":"Secret","metadata":{"name":"%s","namespace":"%s"},"type":"Opaque","data":{"client-id":"%s","client-secret":"%s"}}' \
        "$ACTIVITY_SECRET_NAME" \
        "$ACTIVITY_SECRET_NAMESPACE" \
        "$(encode "$ACTIVITY_CLIENT_ID")" \
        "$(encode "$activity_client_secret")" | \
        kubectl --context "$KUBE_CONTEXT" apply -f - >/dev/null
    unset activity_client_secret

    printf '[OK] ShopSphere Keycloak event policy, client policies, and activity-reader role were reconciled.\n'
    printf '[OK] The activity-reader credential was reconciled into Secret %s/%s.\n' \
        "$ACTIVITY_SECRET_NAMESPACE" "$ACTIVITY_SECRET_NAME"
    printf '[INFO] No administrator credentials, tokens, or client secrets were displayed.\n'
}

main "$@"
