#!/usr/bin/env bash
set -Eeuo pipefail

KUBE_CONTEXT="kind-shopsphere-poc"

export KC_BOOTSTRAP_ADMIN_USERNAME="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-platform get secret shopsphere-keycloak-credentials -o jsonpath='{.data.bootstrap-admin-username}' | base64 -d)"
export KC_BOOTSTRAP_ADMIN_PASSWORD="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-platform get secret shopsphere-keycloak-credentials -o jsonpath='{.data.bootstrap-admin-password}' | base64 -d)"

echo "[INFO] Finding pods..."
keycloak_pod="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-platform get pod -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')"
api_gateway_pod="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps get pod -l app.kubernetes.io/name=api-gateway -o jsonpath='{.items[0].metadata.name}')"
customer_pod="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps get pod -l app.kubernetes.io/name=customer-service -o jsonpath='{.items[0].metadata.name}')"

echo "[INFO] Creating test users in Keycloak via kcadm.sh..."
kubectl --context "$KUBE_CONTEXT" -n shopsphere-platform exec -i "$keycloak_pod" -- bash -ec '
    kcadm=/opt/keycloak/bin/kcadm.sh
    config=/tmp/kcadm.config
    "$kcadm" config credentials --server http://127.0.0.1:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" --config "$config" >/dev/null 2>&1
    
    "$kcadm" create users -r shopsphere -s username=test-ops -s enabled=true -s email=ops@test.com --config "$config" >/dev/null 2>&1 || true
    "$kcadm" set-password -r shopsphere --username test-ops --new-password test1234 --config "$config" >/dev/null 2>&1 || true
    "$kcadm" create users -r shopsphere -s username=test-cust -s enabled=true -s email=cust@test.com --config "$config" >/dev/null 2>&1 || true
    "$kcadm" set-password -r shopsphere --username test-cust --new-password test1234 --config "$config" >/dev/null 2>&1 || true
    
    "$kcadm" add-roles -r shopsphere --uusername test-ops --rolename operations_admin --config "$config" >/dev/null 2>&1 || true
    "$kcadm" add-roles -r shopsphere --uusername test-cust --rolename customer --config "$config" >/dev/null 2>&1 || true
'

echo "[INFO] Retrieving tokens..."
customer_token="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps exec -i "$customer_pod" -- python3 -c '
import json, urllib.request, urllib.parse
req = urllib.request.Request(
    "http://keycloak.shopsphere-platform.svc.cluster.local:8080/realms/shopsphere/protocol/openid-connect/token",
    data=urllib.parse.urlencode({"grant_type": "password", "client_id": "shopsphere-frontend", "username": "test-cust", "password": "test1234"}).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(req) as resp:
    print(json.load(resp)["access_token"])
')"

ops_token="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps exec -i "$customer_pod" -- python3 -c '
import json, urllib.request, urllib.parse
req = urllib.request.Request(
    "http://keycloak.shopsphere-platform.svc.cluster.local:8080/realms/shopsphere/protocol/openid-connect/token",
    data=urllib.parse.urlencode({"grant_type": "password", "client_id": "shopsphere-frontend", "username": "test-ops", "password": "test1234"}).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(req) as resp:
    print(json.load(resp)["access_token"])
')"

echo "[INFO] Testing unauthorized customer access..."
response_code="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps exec -i "$api_gateway_pod" -- curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $customer_token" http://localhost:8000/api/v1/operations/dashboard)"
if [[ "$response_code" == "401" || "$response_code" == "403" ]]; then
    echo "[OK] Customer access correctly rejected ($response_code)."
else
    echo "[ERROR] Customer access returned $response_code."
    exit 1
fi

echo "[INFO] Testing operations_admin dashboard access..."
dashboard_out="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps exec -i "$api_gateway_pod" -- curl -s -f -H "Authorization: Bearer $ops_token" http://localhost:8000/api/v1/operations/dashboard)"
if echo "$dashboard_out" | grep -q "services_health"; then
    echo "[OK] operations_admin successfully retrieved dashboard data."
else
    echo "[ERROR] Invalid operations dashboard response."
    echo "$dashboard_out"
    exit 1
fi

echo "[INFO] Testing executive business KPI dashboard access..."
kpi_out="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps exec -i "$api_gateway_pod" -- curl -s -f -H "Authorization: Bearer $ops_token" http://localhost:8000/api/v1/dashboard/summary)"
if echo "$kpi_out" | grep -q "total_orders"; then
    echo "[OK] Executive business data retrieved."
else
    echo "[ERROR] Invalid KPI dashboard response."
    echo "$kpi_out"
    exit 1
fi

echo "[OK] API Gateway analytics routes successfully verified."
