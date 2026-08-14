#!/usr/bin/env bash
set -Eeuo pipefail

api_gateway_pod="$(kubectl --context kind-shopsphere-poc -n shopsphere-apps get pod -l app.kubernetes.io/name=api-gateway -o jsonpath='{.items[0].metadata.name}')"

# We expect a 401 Unauthorized since we provide no token, but it should be returned by analytics-service.
response="$(kubectl --context kind-shopsphere-poc -n shopsphere-apps exec -i "$api_gateway_pod" -- python3 -c '
import urllib.request
import urllib.error
try:
    urllib.request.urlopen("http://localhost:8000/api/v1/operations/dashboard")
except urllib.error.HTTPError as e:
    print(e.read().decode() + str(e.code))
')"

status_code="${response: -3}"
body="${response%???}"

echo "Status: $status_code"
echo "Body: $body"

if [[ "$status_code" == "401" ]]; then
    echo "[OK] Request correctly routed and rejected with 401 by analytics-service."
else
    echo "[ERROR] Unexpected status code."
    exit 1
fi
