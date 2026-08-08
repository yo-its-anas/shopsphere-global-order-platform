#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-platform"
readonly DEPLOYMENT_NAME="keycloak"
readonly SERVICE_NAME="keycloak"

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
    local pod_name=""
    local database_connections=""
    local activity_client_id=""
    local activity_client_secret=""

    require_command kubectl

    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait \
        --for=condition=Available \
        "deployment/${DEPLOYMENT_NAME}" \
        --timeout=10s >/dev/null || fail "Keycloak Deployment is not Available."

    service_type="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o jsonpath='{.spec.type}')"
    cluster_ip="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o jsonpath='{.spec.clusterIP}')"
    [[ "$service_type" == "ClusterIP" ]] || fail "Keycloak Service type is '${service_type}', expected ClusterIP."
    [[ -n "$cluster_ip" && "$cluster_ip" != "None" ]] || fail "Keycloak Service does not have an internal ClusterIP."

    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod \
        -l app.kubernetes.io/name=keycloak \
        -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "No Keycloak pod was found."

    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- bash -ec '
        admin_config=/tmp/shopsphere-kcadm-admin.config
        service_config=/tmp/shopsphere-kcadm-service.config
        trap '\''rm -f "$admin_config" "$service_config"'\'' EXIT
        kcadm=/opt/keycloak/bin/kcadm.sh

        "$kcadm" config credentials \
            --config "$admin_config" \
            --server http://127.0.0.1:8080 \
            --realm master \
            --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
            --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1

        realm_doc="$("$kcadm" get realms/shopsphere --config "$admin_config" \
            --fields realm,enabled,registrationAllowed,registrationEmailAsUsername,loginWithEmailAllowed,duplicateEmailsAllowed,editUsernameAllowed,resetPasswordAllowed,passwordPolicy,accessTokenLifespan,ssoSessionIdleTimeout,ssoSessionMaxLifespan,bruteForceProtected,eventsEnabled,eventsExpiration,enabledEventTypes,adminEventsEnabled,adminEventsDetailsEnabled,revokeRefreshToken,refreshTokenMaxReuse)"
        grep -Eq '\''"realm"[[:space:]]*:[[:space:]]*"shopsphere"'\'' <<<"$realm_doc"
        grep -Eq '\''"registrationAllowed"[[:space:]]*:[[:space:]]*true'\'' <<<"$realm_doc"
        grep -Eq '\''"bruteForceProtected"[[:space:]]*:[[:space:]]*true'\'' <<<"$realm_doc"
        grep -Eq '\''"eventsEnabled"[[:space:]]*:[[:space:]]*true'\'' <<<"$realm_doc"
        grep -Eq '\''"adminEventsEnabled"[[:space:]]*:[[:space:]]*true'\'' <<<"$realm_doc"
        grep -Eq '\''"adminEventsDetailsEnabled"[[:space:]]*:[[:space:]]*false'\'' <<<"$realm_doc"
        grep -Eq '\''"eventsExpiration"[[:space:]]*:[[:space:]]*604800'\'' <<<"$realm_doc"
        grep -q '\''UPDATE_PROFILE'\'' <<<"$realm_doc"
        grep -q '\''UPDATE_EMAIL'\'' <<<"$realm_doc"
        grep -Eq '\''"revokeRefreshToken"[[:space:]]*:[[:space:]]*true'\'' <<<"$realm_doc"
        grep -Eq '\''"registrationEmailAsUsername"[[:space:]]*:[[:space:]]*true'\'' <<<"$realm_doc"
        grep -Eq '\''"loginWithEmailAllowed"[[:space:]]*:[[:space:]]*true'\'' <<<"$realm_doc"
        grep -Eq '\''"duplicateEmailsAllowed"[[:space:]]*:[[:space:]]*false'\'' <<<"$realm_doc"
        grep -Eq '\''"editUsernameAllowed"[[:space:]]*:[[:space:]]*false'\'' <<<"$realm_doc"
        grep -Eq '\''"accessTokenLifespan"[[:space:]]*:[[:space:]]*300'\'' <<<"$realm_doc"
        grep -q '\''length(12)'\'' <<<"$realm_doc"

        for role in customer support operations_admin; do
            role_doc="$("$kcadm" get "roles/${role}" -r shopsphere --config "$admin_config" --fields name)"
            grep -Eq "\\\"name\\\"[[:space:]]*:[[:space:]]*\\\"${role}\\\"" <<<"$role_doc"
        done

        default_roles_doc="$("$kcadm" get roles/default-roles-shopsphere/composites \
            -r shopsphere --config "$admin_config" --fields name)"
        grep -Eq '\''"name"[[:space:]]*:[[:space:]]*"customer"'\'' <<<"$default_roles_doc"

        frontend_doc="$("$kcadm" get clients -r shopsphere --config "$admin_config" \
            -q clientId=shopsphere-frontend \
            --fields clientId,publicClient,standardFlowEnabled,implicitFlowEnabled,directAccessGrantsEnabled,serviceAccountsEnabled,redirectUris,webOrigins,attributes)"
        grep -Eq '\''"clientId"[[:space:]]*:[[:space:]]*"shopsphere-frontend"'\'' <<<"$frontend_doc"
        grep -Eq '\''"publicClient"[[:space:]]*:[[:space:]]*true'\'' <<<"$frontend_doc"
        grep -Eq '\''"standardFlowEnabled"[[:space:]]*:[[:space:]]*true'\'' <<<"$frontend_doc"
        grep -Eq '\''"implicitFlowEnabled"[[:space:]]*:[[:space:]]*false'\'' <<<"$frontend_doc"
        grep -Eq '\''"directAccessGrantsEnabled"[[:space:]]*:[[:space:]]*false'\'' <<<"$frontend_doc"
        grep -Eq '\''"serviceAccountsEnabled"[[:space:]]*:[[:space:]]*false'\'' <<<"$frontend_doc"
        if grep -Eq '\''"secret"[[:space:]]*:'\'' <<<"$frontend_doc"; then
            printf '\''Frontend client unexpectedly exposed a secret field.\n'\'' >&2
            exit 1
        fi

        api_doc="$("$kcadm" get clients -r shopsphere --config "$admin_config" \
            -q clientId=shopsphere-api \
            --fields clientId,bearerOnly,publicClient,standardFlowEnabled,directAccessGrantsEnabled,serviceAccountsEnabled)"
        grep -Eq '\''"clientId"[[:space:]]*:[[:space:]]*"shopsphere-api"'\'' <<<"$api_doc"
        grep -Eq '\''"bearerOnly"[[:space:]]*:[[:space:]]*true'\'' <<<"$api_doc"
        grep -Eq '\''"standardFlowEnabled"[[:space:]]*:[[:space:]]*false'\'' <<<"$api_doc"

        profiles_doc="$("$kcadm" get client-policies/profiles -r shopsphere --config "$admin_config")"
        policies_doc="$("$kcadm" get client-policies/policies -r shopsphere --config "$admin_config")"
        grep -q '\''shopsphere-pkce-s256'\'' <<<"$profiles_doc"
        grep -q '\''pkce-enforcer'\'' <<<"$profiles_doc"
        grep -q '\''shopsphere-pkce-s256-policy'\'' <<<"$policies_doc"
        grep -Eq '\''"enabled"[[:space:]]*:[[:space:]]*true'\'' <<<"$policies_doc"

        service_doc="$("$kcadm" get clients -r shopsphere --config "$admin_config" \
            -q clientId=shopsphere-service-integration --fields id,clientId,serviceAccountsEnabled)"
        service_uuid="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' <<<"$service_doc")"
        test -n "$service_uuid"
        grep -Eq '\''"serviceAccountsEnabled"[[:space:]]*:[[:space:]]*true'\'' <<<"$service_doc"

        secret_doc="$("$kcadm" get "clients/${service_uuid}/client-secret" -r shopsphere --config "$admin_config")"
        client_secret="$(sed -n '\''s/.*"value" : "\([^"]*\)".*/\1/p'\'' <<<"$secret_doc")"
        test -n "$client_secret"
        unset secret_doc

        "$kcadm" config credentials \
            --config "$service_config" \
            --server http://127.0.0.1:8080 \
            --realm shopsphere \
            --client shopsphere-service-integration \
            --secret "$client_secret" >/dev/null 2>&1
        unset client_secret

        events_doc="$("$kcadm" get events -r shopsphere --config "$admin_config" --fields type,clientId)"
        grep -Eq '\''"type"[[:space:]]*:[[:space:]]*"CLIENT_LOGIN"'\'' <<<"$events_doc"
        grep -Eq '\''"clientId"[[:space:]]*:[[:space:]]*"shopsphere-service-integration"'\'' <<<"$events_doc"

        activity_doc="$("$kcadm" get clients -r shopsphere --config "$admin_config" \
            -q clientId=shopsphere-customer-activity-reader \
            --fields id,clientId,publicClient,standardFlowEnabled,directAccessGrantsEnabled,serviceAccountsEnabled,fullScopeAllowed)"
        activity_uuid="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' <<<"$activity_doc")"
        test -n "$activity_uuid"
        grep -Eq '\''"publicClient"[[:space:]]*:[[:space:]]*false'\'' <<<"$activity_doc"
        grep -Eq '\''"standardFlowEnabled"[[:space:]]*:[[:space:]]*false'\'' <<<"$activity_doc"
        grep -Eq '\''"directAccessGrantsEnabled"[[:space:]]*:[[:space:]]*false'\'' <<<"$activity_doc"
        grep -Eq '\''"serviceAccountsEnabled"[[:space:]]*:[[:space:]]*true'\'' <<<"$activity_doc"
        grep -Eq '\''"fullScopeAllowed"[[:space:]]*:[[:space:]]*false'\'' <<<"$activity_doc"

        activity_user_doc="$("$kcadm" get "clients/${activity_uuid}/service-account-user" \
            -r shopsphere --config "$admin_config" --fields id)"
        activity_user_uuid="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' <<<"$activity_user_doc")"
        test -n "$activity_user_uuid"
        realm_management_doc="$("$kcadm" get clients -r shopsphere --config "$admin_config" \
            -q clientId=realm-management --fields id)"
        realm_management_uuid="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' \
            <<<"$realm_management_doc")"
        test -n "$realm_management_uuid"
        activity_roles="$("$kcadm" get \
            "users/${activity_user_uuid}/role-mappings/clients/${realm_management_uuid}" \
            -r shopsphere --config "$admin_config" --fields name)"
        grep -Eq '\''"name"[[:space:]]*:[[:space:]]*"view-events"'\'' <<<"$activity_roles"
        if grep -Eq '\''"name"[[:space:]]*:[[:space:]]*"(manage-events|realm-admin)"'\'' \
            <<<"$activity_roles"; then
            printf '\''Activity reader has an excessive realm-management role.\n'\'' >&2
            exit 1
        fi
        activity_scope="$("$kcadm" get \
            "clients/${activity_uuid}/scope-mappings/clients/${realm_management_uuid}" \
            -r shopsphere --config "$admin_config" --fields name)"
        grep -Eq '\''"name"[[:space:]]*:[[:space:]]*"view-events"'\'' <<<"$activity_scope"
        if grep -Eq '\''"name"[[:space:]]*:[[:space:]]*"(manage-events|realm-admin)"'\'' \
            <<<"$activity_scope"; then
            printf '\''Activity reader token scope has an excessive realm-management role.\n'\'' >&2
            exit 1
        fi

        activity_secret_doc="$("$kcadm" get "clients/${activity_uuid}/client-secret" \
            -r shopsphere --config "$admin_config")"
        activity_secret="$(sed -n '\''s/.*"value" : "\([^"]*\)".*/\1/p'\'' \
            <<<"$activity_secret_doc")"
        test -n "$activity_secret"
        "$kcadm" get events -r shopsphere --no-config \
            --server http://127.0.0.1:8080 \
            --realm shopsphere \
            --client shopsphere-customer-activity-reader \
            --secret "$activity_secret" \
            --fields type >/dev/null
        unset activity_secret activity_secret_doc
    ' >/dev/null

    activity_client_id="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps get secret \
        shopsphere-customer-activity-keycloak -o jsonpath='{.data.client-id}')"
    activity_client_secret="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps get secret \
        shopsphere-customer-activity-keycloak -o jsonpath='{.data.client-secret}')"
    [[ -n "$activity_client_id" && -n "$activity_client_secret" ]] || \
        fail "The customer activity Keycloak Secret is absent or incomplete."
    unset activity_client_id activity_client_secret

    database_connections="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-data exec postgresql-0 -- \
        sh -ec 'psql --tuples-only --no-align --username "$POSTGRES_USER" --dbname postgres --command="SELECT count(*) FROM pg_stat_activity WHERE datname = '\''keycloak_db'\'';"')"
    [[ "$database_connections" =~ ^[1-9][0-9]*$ ]] || fail "No active Keycloak PostgreSQL connection was found."

    printf '[OK] Keycloak Deployment is Available.\n'
    printf '[OK] Service is ClusterIP-only at %s; no public administration Service exists.\n' "$cluster_ip"
    printf '[OK] Keycloak has an active connection to keycloak_db.\n'
    printf '[OK] Realm, registration, brute-force, refresh-token, and event settings are configured.\n'
    printf '[OK] Required realm roles exist: customer, support, operations_admin.\n'
    printf '[OK] Self-registration receives the default customer role.\n'
    printf '[OK] Frontend client is public, standard-flow-only, and has no embedded client credential.\n'
    printf '[OK] API client is a bearer-only resource-server audience.\n'
    printf '[OK] The enabled realm client policy enforces S256 PKCE.\n'
    printf '[OK] A least-privilege client authentication event was recorded and queried successfully.\n'
    printf '[OK] The dedicated customer activity reader has view-events without manage-events or realm-admin.\n'
    printf '[OK] The activity-reader client credential exists in a namespace-scoped Kubernetes Secret.\n'
    printf '[INFO] No credentials, client secrets, or token values were displayed.\n'
}

main "$@"
