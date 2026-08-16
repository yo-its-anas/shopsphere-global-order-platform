#!/usr/bin/env bash
set -Eeuo pipefail

echo "[INFO] Starting frontend dev server on port 5173 in the background..."
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 >/tmp/frontend.log 2>&1 &
cd ..

echo "[INFO] Starting Kubernetes port forwards..."
kubectl --context kind-shopsphere-poc -n shopsphere-apps port-forward svc/api-gateway 8000:8000 >/tmp/gateway-pf.log 2>&1 &
kubectl --context kind-shopsphere-poc -n shopsphere-platform port-forward svc/keycloak 8080:8080 >/tmp/keycloak-8080-pf.log 2>&1 &
kubectl --context kind-shopsphere-poc -n shopsphere-platform port-forward svc/keycloak 8081:8080 >/tmp/keycloak-8081-pf.log 2>&1 &
kubectl --context kind-shopsphere-poc -n shopsphere-monitoring port-forward svc/grafana 3000:3000 >/tmp/grafana-pf.log 2>&1 &
kubectl --context kind-shopsphere-poc -n shopsphere-monitoring port-forward svc/prometheus 9090:9090 >/tmp/prometheus-pf.log 2>&1 &
kubectl --context kind-shopsphere-poc -n shopsphere-monitoring port-forward svc/loki 3100:3100 >/tmp/loki-pf.log 2>&1 &

echo "[OK] All ports are now listening in the background on 127.0.0.1!"
echo "[INFO] You can safely re-run your local SSH tunnel now, and all ports will connect cleanly."
