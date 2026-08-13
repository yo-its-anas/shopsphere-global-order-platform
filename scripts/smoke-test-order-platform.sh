#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly KEYCLOAK_NAMESPACE="shopsphere-platform"
readonly APP_NAMESPACE="shopsphere-apps"
readonly DATA_NAMESPACE="shopsphere-data"
readonly SMOKE_CLIENT_ID="shopsphere-order-deployment-smoke"

keycloak_pod=""
client_uuid=""
client_secret=""

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

cleanup() {
    [[ -n "$client_uuid" && -n "$keycloak_pod" ]] || return 0
    kubectl --context "$KUBE_CONTEXT" -n "$KEYCLOAK_NAMESPACE" exec "$keycloak_pod" -- \
        bash -ec '
            config=/tmp/shopsphere-order-smoke-cleanup.config
            trap '\''rm -f "$config"'\'' EXIT
            kcadm=/opt/keycloak/bin/kcadm.sh
            "$kcadm" config credentials --config "$config" \
                --server http://127.0.0.1:8080 --realm master \
                --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
                --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1
            "$kcadm" delete "clients/'"$client_uuid"'" -r shopsphere \
                --config "$config" >/dev/null
        ' >/dev/null 2>&1 || printf '[ERROR] Temporary Keycloak client cleanup failed.\n' >&2
    client_uuid=""
    unset client_secret
}

main() {
    local api_gateway_pod=""
    local order_pod=""
    local postgresql_pod=""
    local product_id=""
    local credential_document=""
    local customer_token=""
    local order_id=""

    command -v kubectl >/dev/null 2>&1 || fail "Required command 'kubectl' was not found."
    keycloak_pod="$(kubectl --context "$KUBE_CONTEXT" -n "$KEYCLOAK_NAMESPACE" get pod \
        -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')"
    api_gateway_pod="$(kubectl --context "$KUBE_CONTEXT" -n "$APP_NAMESPACE" get pod \
        -l app.kubernetes.io/name=api-gateway -o jsonpath='{.items[0].metadata.name}')"
    order_pod="$(kubectl --context "$KUBE_CONTEXT" -n "$APP_NAMESPACE" get pod \
        -l app.kubernetes.io/name=order-service -o jsonpath='{.items[0].metadata.name}')"
    postgresql_pod="$(kubectl --context "$KUBE_CONTEXT" -n "$DATA_NAMESPACE" get pod \
        -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$keycloak_pod" && -n "$api_gateway_pod" && -n "$order_pod" && \
        -n "$postgresql_pod" ]] || fail "A required PoC pod was not found."
    trap cleanup EXIT

    product_id="$(kubectl --context "$KUBE_CONTEXT" -n "$DATA_NAMESPACE" \
        exec "$postgresql_pod" -- sh -ec '
            psql --username "$POSTGRES_USER" --dbname catalogue_db \
                --tuples-only --no-align --no-psqlrc --command="
                    SELECT p.id
                    FROM products p
                    JOIN product_prices pp
                      ON pp.product_id = p.id
                     AND pp.is_active = true
                     AND pp.currency_code = '\''USD'\''
                    JOIN inventory_items i ON i.product_id = p.id
                    WHERE p.status = '\''active'\''
                      AND p.is_searchable = true
                      AND i.quantity_on_hand - i.quantity_reserved > 0
                    ORDER BY p.created_at
                    LIMIT 1;"
        ' | tr -d '[:space:]')"
    [[ -n "$product_id" ]] || fail "No active USD-priced product with available stock exists."

    credential_document="$(kubectl --context "$KUBE_CONTEXT" -n "$KEYCLOAK_NAMESPACE" \
        exec "$keycloak_pod" -- bash -ec '
            config=/tmp/shopsphere-order-smoke.config
            mapper=/tmp/shopsphere-order-smoke-audience.json
            trap '\''rm -f "$config" "$mapper"'\'' EXIT
            kcadm=/opt/keycloak/bin/kcadm.sh
            client_id='"$SMOKE_CLIENT_ID"'
            "$kcadm" config credentials --config "$config" \
                --server http://127.0.0.1:8080 --realm master \
                --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
                --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1
            existing="$("$kcadm" get clients -r shopsphere --config "$config" \
                -q clientId="$client_id" --fields id)"
            existing_id="$(sed -n '\''s/.*"id" : "\([^"]*\)".*/\1/p'\'' <<<"$existing")"
            if [[ -n "$existing_id" ]]; then
                "$kcadm" delete "clients/${existing_id}" -r shopsphere \
                    --config "$config" >/dev/null
            fi
            uuid="$("$kcadm" create clients -r shopsphere --config "$config" -i \
                -s clientId="$client_id" -s enabled=true -s protocol=openid-connect \
                -s publicClient=false -s clientAuthenticatorType=client-secret \
                -s standardFlowEnabled=false -s implicitFlowEnabled=false \
                -s directAccessGrantsEnabled=false -s serviceAccountsEnabled=true \
                -s fullScopeAllowed=true)"
            account="$("$kcadm" get "clients/${uuid}/service-account-user" \
                -r shopsphere --config "$config" --fields username)"
            username="$(sed -n '\''s/.*"username" : "\([^"]*\)".*/\1/p'\'' <<<"$account")"
            "$kcadm" add-roles -r shopsphere --config "$config" \
                --uusername "$username" --rolename customer >/dev/null
            printf '\''{"name":"shopsphere-api-audience","protocol":"openid-connect","protocolMapper":"oidc-audience-mapper","consentRequired":false,"config":{"included.client.audience":"shopsphere-api","access.token.claim":"true","id.token.claim":"false","introspection.token.claim":"true"}}'\'' >"$mapper"
            "$kcadm" create "clients/${uuid}/protocol-mappers/models" \
                -r shopsphere --config "$config" -f "$mapper" >/dev/null
            secret_doc="$("$kcadm" get "clients/${uuid}/client-secret" \
                -r shopsphere --config "$config")"
            secret="$(sed -n '\''s/.*"value" : "\([^"]*\)".*/\1/p'\'' <<<"$secret_doc")"
            test -n "$uuid" && test -n "$secret"
            printf '\''%s\n%s'\'' "$uuid" "$secret"
        ')"
    client_uuid="${credential_document%%$'\n'*}"
    client_secret="${credential_document#*$'\n'}"
    [[ -n "$client_uuid" && -n "$client_secret" ]] || fail "Smoke client setup failed."

    customer_token="$(printf '%s' "$client_secret" | kubectl --context "$KUBE_CONTEXT" \
        -n "$APP_NAMESPACE" exec -i "$order_pod" -- \
        env SMOKE_CLIENT_ID="$SMOKE_CLIENT_ID" python -c '
import json
import os
import sys
import urllib.parse
import urllib.request

request = urllib.request.Request(
    os.environ["SERVICE_TOKEN_URL"],
    data=urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": os.environ["SMOKE_CLIENT_ID"],
            "client_secret": sys.stdin.read(),
        }
    ).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=10) as response:
    print(json.load(response)["access_token"])
    ')"
    unset client_secret credential_document
    [[ -n "$customer_token" ]] || fail "Smoke token acquisition failed."

    order_id="$(printf '%s' "$customer_token" | kubectl --context "$KUBE_CONTEXT" \
        -n "$APP_NAMESPACE" exec -i "$api_gateway_pod" -- \
        env PRODUCT_ID="$product_id" python -c '
import json
import os
import sys
import urllib.request

base = "http://127.0.0.1:8000/api/v1"
headers = {"Authorization": "Bearer " + sys.stdin.read(), "Content-Type": "application/json"}

def call(method, path, body=None, request_id="order-deployment-smoke", extra_headers=None):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={**headers, "X-Request-ID": request_id, **(extra_headers or {})},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)

call("GET", "/carts/me", request_id="order-deployment-smoke-cart")
call(
    "POST",
    "/carts/me/items",
    {"product_id": os.environ["PRODUCT_ID"], "quantity": 1},
    "order-deployment-smoke-item",
)
order = call(
    "POST",
    "/orders/checkout",
    request_id="order-deployment-smoke-checkout",
    extra_headers={"Idempotency-Key": "order-deployment-smoke-checkout-v1"},
)
call(
    "POST",
    "/orders/me/" + order["order_id"] + "/cancellation",
    request_id="order-deployment-smoke-cancel",
)
print(order["order_id"])
    ')"
    unset customer_token
    [[ "$order_id" =~ ^[0-9a-f-]{36}$ ]] || fail "Smoke checkout returned no valid order ID."

    kubectl --context "$KUBE_CONTEXT" -n "$APP_NAMESPACE" exec "$order_pod" -- \
        env SMOKE_ORDER_ID="$order_id" python -c '
import os
import time
import psycopg

database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
expected = {
    "order.created.v1",
    "order.confirmed.v1",
    "order.status_changed.v1",
    "order.cancelled.v1",
}
with psycopg.connect(database_url, connect_timeout=3) as connection:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        rows = connection.execute(
            "SELECT event_type, status FROM order_event_outbox WHERE aggregate_id = %s::uuid",
            (os.environ["SMOKE_ORDER_ID"],),
        ).fetchall()
        states = {event_type: status for event_type, status in rows}
        if expected.issubset(states) and all(states[event] == "published" for event in expected):
            break
        time.sleep(1)
    else:
        raise AssertionError("Order outbox events did not all reach published state")
print("published=" + ",".join(sorted(expected)))
    '

    printf '[OK] Gateway checkout and cancellation succeeded for simulated data; inventory was released and Order outbox events were broker-acknowledged.\n'
    printf '[INFO] Simulated cancelled order ID: %s\n' "$order_id"
    printf '[INFO] The temporary Keycloak client will be removed; no credential or token was displayed.\n'
}

main "$@"
