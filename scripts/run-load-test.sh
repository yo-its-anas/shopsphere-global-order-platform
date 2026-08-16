#!/usr/bin/env bash
set -Eeuo pipefail

echo "[INFO] Setting up port forwarding..."
kubectl --context kind-shopsphere-poc -n shopsphere-apps port-forward svc/api-gateway 8000:8000 >/dev/null 2>&1 &
GATEWAY_PID=$!

kubectl --context kind-shopsphere-poc -n shopsphere-platform port-forward svc/keycloak 8080:8080 >/dev/null 2>&1 &
KEYCLOAK_PID=$!

cleanup() {
  echo "[INFO] Cleaning up port forwards..."
  kill $GATEWAY_PID $KEYCLOAK_PID || true
}
trap cleanup EXIT

echo "[INFO] Waiting for port forwards to establish..."
sleep 5

echo "[INFO] Ensuring operations@yopmail.com has password TestPassword@1234..."
keycloak_pod="$(kubectl --context kind-shopsphere-poc -n shopsphere-platform get pod -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')"
export KC_BOOTSTRAP_ADMIN_USERNAME="$(kubectl --context kind-shopsphere-poc -n shopsphere-platform get secret shopsphere-keycloak-credentials -o jsonpath='{.data.bootstrap-admin-username}' | base64 -d)"
export KC_BOOTSTRAP_ADMIN_PASSWORD="$(kubectl --context kind-shopsphere-poc -n shopsphere-platform get secret shopsphere-keycloak-credentials -o jsonpath='{.data.bootstrap-admin-password}' | base64 -d)"

kubectl --context kind-shopsphere-poc -n shopsphere-platform exec -i "$keycloak_pod" -- bash -ec '
    kcadm=/opt/keycloak/bin/kcadm.sh
    config=/tmp/kcadm.config
    "$kcadm" config credentials --server http://127.0.0.1:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" --config "$config" >/dev/null 2>&1
    
    echo "[INFO] Updating operations@yopmail.com user profile..."
    user_id=$("$kcadm" get users -r shopsphere -q username=operations@yopmail.com --fields id --format csv --config "$config" | head -n 1 | tr -d "\042")
    if [ ! -z "$user_id" ]; then
        "$kcadm" update "users/${user_id}" -r shopsphere -s emailVerified=true -s requiredActions=[] --config "$config"
        "$kcadm" set-password -r shopsphere --username operations@yopmail.com --new-password TestPassword@1234 --temporary=false --config "$config" || true
    else
        echo "[ERROR] operations@yopmail.com not found!"
    fi
'

echo "[INFO] Running load test script..."
# Run the python load test using analytics-service virtualenv which has httpx2
services/analytics-service/.venv/bin/python tests/performance/load_test.py
