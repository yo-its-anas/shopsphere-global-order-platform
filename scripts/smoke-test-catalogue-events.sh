#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly KEYCLOAK_NAMESPACE="shopsphere-platform"
readonly APP_NAMESPACE="shopsphere-apps"
readonly SMOKE_CLIENT_ID="shopsphere-catalogue-event-smoke"

keycloak_pod=""
client_uuid=""
client_secret=""

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

remove_test_client() {
    [[ -n "$client_uuid" && -n "$keycloak_pod" ]] || return 0
    if ! kubectl --context "$KUBE_CONTEXT" -n "$KEYCLOAK_NAMESPACE" exec "$keycloak_pod" -- \
        bash -ec '
            config=/tmp/shopsphere-event-smoke-cleanup.config
            trap '\''rm -f "$config"'\'' EXIT
            kcadm=/opt/keycloak/bin/kcadm.sh
            "$kcadm" config credentials --config "$config" \
                --server http://127.0.0.1:8080 --realm master \
                --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
                --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1
            "$kcadm" delete "clients/'"$client_uuid"'" \
                -r shopsphere --config "$config" >/dev/null
        ' >/dev/null 2>&1; then
        printf '[ERROR] Temporary Keycloak smoke-test client cleanup failed.\n' >&2
        return 1
    fi
    client_uuid=""
}

main() {
    local credential_document=""
    local catalogue_pod=""
    local smoke_suffix=""
    command -v kubectl >/dev/null 2>&1 || fail "Required command 'kubectl' was not found."
    keycloak_pod="$(kubectl --context "$KUBE_CONTEXT" -n "$KEYCLOAK_NAMESPACE" get pod \
        -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')"
    catalogue_pod="$(kubectl --context "$KUBE_CONTEXT" -n "$APP_NAMESPACE" get pod \
        -l app.kubernetes.io/name=catalogue-service -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$keycloak_pod" && -n "$catalogue_pod" ]] || fail "Required pods were not found."
    smoke_suffix="$(date -u +%Y%m%d%H%M%S)"
    trap remove_test_client EXIT

    credential_document="$(kubectl --context "$KUBE_CONTEXT" \
        -n "$KEYCLOAK_NAMESPACE" exec "$keycloak_pod" -- bash -ec '
            config=/tmp/shopsphere-event-smoke.config
            mapper=/tmp/shopsphere-event-smoke-mapper.json
            trap '\''rm -f "$config" "$mapper"'\'' EXIT
            kcadm=/opt/keycloak/bin/kcadm.sh
            client_id='"$SMOKE_CLIENT_ID"'
            "$kcadm" config credentials --config "$config" \
                --server http://127.0.0.1:8080 --realm master \
                --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
                --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1
            existing="$($kcadm get clients -r shopsphere --config "$config" \
                -q clientId="$client_id" --fields id)"
            existing_id="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' <<<"$existing")"
            if [[ -n "$existing_id" ]]; then
                "$kcadm" delete "clients/${existing_id}" -r shopsphere \
                    --config "$config" >/dev/null
            fi
            uuid="$($kcadm create clients -r shopsphere --config "$config" -i \
                -s clientId="$client_id" -s enabled=true -s protocol=openid-connect \
                -s publicClient=false -s clientAuthenticatorType=client-secret \
                -s standardFlowEnabled=false -s implicitFlowEnabled=false \
                -s directAccessGrantsEnabled=false -s serviceAccountsEnabled=true \
                -s fullScopeAllowed=true)"
            account="$($kcadm get "clients/${uuid}/service-account-user" \
                -r shopsphere --config "$config" --fields username)"
            username="$(sed -n '\''s/.*"username" : "\([^"]*\)".*/\1/p'\'' <<<"$account")"
            "$kcadm" add-roles -r shopsphere --config "$config" \
                --uusername "$username" --rolename operations_admin >/dev/null
            printf '\''{"name":"shopsphere-api-audience","protocol":"openid-connect","protocolMapper":"oidc-audience-mapper","consentRequired":false,"config":{"included.client.audience":"shopsphere-api","access.token.claim":"true","id.token.claim":"false","introspection.token.claim":"true"}}'\'' >"$mapper"
            "$kcadm" create "clients/${uuid}/protocol-mappers/models" \
                -r shopsphere --config "$config" -f "$mapper" >/dev/null 2>&1
            secret_doc="$($kcadm get "clients/${uuid}/client-secret" \
                -r shopsphere --config "$config")"
            secret="$(sed -n '\''s/.*"value" : "\([^"]*\)".*/\1/p'\'' <<<"$secret_doc")"
            test -n "$uuid" && test -n "$secret"
            printf '\''%s\n%s'\'' "$uuid" "$secret"
        ')"
    client_uuid="${credential_document%%$'\n'*}"
    client_secret="${credential_document#*$'\n'}"
    [[ -n "$client_uuid" && -n "$client_secret" ]] || fail "Test client setup failed."

    printf '%s' "$client_secret" | kubectl --context "$KUBE_CONTEXT" \
        -n "$APP_NAMESPACE" exec -i "$catalogue_pod" -- \
        env SMOKE_SUFFIX="$smoke_suffix" SMOKE_CLIENT_ID="$SMOKE_CLIENT_ID" python -c '
import json
import os
import sys
import urllib.parse
import urllib.request

secret = sys.stdin.read()
token_request = urllib.request.Request(
    "http://keycloak.shopsphere-platform.svc.cluster.local:8080/realms/shopsphere/protocol/openid-connect/token",
    data=urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": os.environ["SMOKE_CLIENT_ID"],
            "client_secret": secret,
        }
    ).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
with urllib.request.urlopen(token_request, timeout=10) as response:
    token = json.load(response)["access_token"]

base = "http://127.0.0.1:8000/api/v1"
correlation = f"catalogue-event-smoke-{os.environ['"'"'SMOKE_SUFFIX'"'"']}"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def call(method, path, body, request_id):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={**headers, "X-Request-ID": request_id},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)

category = call(
    "POST",
    "/categories",
    {"name": "Kafka Smoke Category", "slug": f"kafka-smoke-{os.environ['"'"'SMOKE_SUFFIX'"'"']}"},
    correlation + "-category",
)
product = call(
    "POST",
    "/products",
    {
        "sku": f"KAFKA-{os.environ['"'"'SMOKE_SUFFIX'"'"']}",
        "name": "Kafka Smoke Product",
        "category_id": category["id"],
        "status": "active",
        "is_searchable": True,
    },
    correlation + "-created",
)
call("PATCH", f"/products/{product['"'"'id'"'"']}", {"name": "Kafka Smoke Product Updated"}, correlation + "-updated")
call("PUT", f"/products/{product['"'"'id'"'"']}/prices/USD", {"amount": "29.9900"}, correlation + "-price")
call(
    "POST",
    f"/inventory/products/{product['"'"'id'"'"']}/initialize",
    {"quantity_on_hand": 3, "reorder_threshold": 2, "reason": "Event smoke initialization", "idempotency_key": correlation + "-init"},
    correlation + "-inventory-init",
)
call(
    "POST",
    f"/inventory/products/{product['"'"'id'"'"']}/adjustments",
    {"movement_type": "DAMAGE", "quantity_delta": -1, "reason": "Event smoke low-stock transition", "idempotency_key": correlation + "-low"},
    correlation + "-inventory-low",
)
call(
    "POST",
    f"/inventory/products/{product['"'"'id'"'"']}/adjustments",
    {"movement_type": "DAMAGE", "quantity_delta": -2, "reason": "Event smoke out-of-stock transition", "idempotency_key": correlation + "-empty"},
    correlation + "-inventory-empty",
)
print(json.dumps({"correlation_prefix": correlation, "product_id": product["id"], "operations": 6}))
'
    unset client_secret credential_document
    printf '[OK] Simulated catalogue operations committed without displaying credentials or tokens.\n'
}

main "$@"
