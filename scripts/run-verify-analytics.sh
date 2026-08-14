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

export KC_BOOTSTRAP_ADMIN_USERNAME="$(kubectl --context kind-shopsphere-poc -n shopsphere-platform get secret shopsphere-keycloak-credentials -o jsonpath='{.data.bootstrap-admin-username}' | base64 -d)"
export KC_BOOTSTRAP_ADMIN_PASSWORD="$(kubectl --context kind-shopsphere-poc -n shopsphere-platform get secret shopsphere-keycloak-credentials -o jsonpath='{.data.bootstrap-admin-password}' | base64 -d)"

echo "[INFO] Running verification script..."
python3 scripts/verify-analytics.py
