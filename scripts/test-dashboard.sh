#!/usr/bin/env bash
set -Eeuo pipefail

KUBE_CONTEXT="kind-shopsphere-poc"

api_gateway_pod="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps get pod -l app.kubernetes.io/name=api-gateway -o jsonpath='{.items[0].metadata.name}')"
order_pod="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps get pod -l app.kubernetes.io/name=order-service -o jsonpath='{.items[0].metadata.name}')"

echo "[INFO] Retrieving operations_admin token..."
ops_token="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps exec -i "$order_pod" -- python3 -c '
import json, urllib.request, urllib.parse, sys
req = urllib.request.Request(
    "http://keycloak.shopsphere-platform.svc.cluster.local:8080/realms/shopsphere/protocol/openid-connect/token",
    data=urllib.parse.urlencode({"grant_type": "password", "client_id": "shopsphere-frontend", "username": "test-ops", "password": "test1234"}).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
try:
    with urllib.request.urlopen(req) as resp:
        print(json.load(resp)["access_token"])
except urllib.error.HTTPError as e:
    print(e.read().decode(), file=sys.stderr)
    sys.exit(1)
')"

echo "[INFO] Testing operations_admin dashboard access..."
response="$(kubectl --context "$KUBE_CONTEXT" -n shopsphere-apps exec -i "$api_gateway_pod" -- python3 -c '
import json, urllib.request, urllib.parse, sys
req = urllib.request.Request(
    "http://localhost:8000/api/v1/operations/dashboard",
    headers={"Authorization": "Bearer '"$ops_token"'"}
)
try:
    with urllib.request.urlopen(req) as resp:
        print(json.dumps(json.load(resp), indent=2))
except urllib.error.HTTPError as e:
    print("HTTPError: " + str(e.code) + " " + e.read().decode(), file=sys.stderr)
    sys.exit(1)
')"

echo "$response"

if echo "$response" | grep -q "services_health"; then
    echo "[OK] operations_admin successfully retrieved dashboard data."
else
    echo "[ERROR] Dashboard structure invalid."
    exit 1
fi
