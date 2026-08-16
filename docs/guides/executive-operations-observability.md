# ShopSphere Executive Operations & Observability Demonstration Guide

This guide describes step-by-step procedures to demonstrate three core SRE, Observability, and SecOps capabilities of the ShopSphere Enterprise Platform PoC. 

These demonstrations directly answer academic and engineering boards regarding how business KPI metrics are aggregated, how requests are tracked dynamically, and how service failures/recoveries are observed and self-healed.

---

## Demo A — Executive Business Dashboard

This demo illustrates real-time business KPI aggregation on the **Executive Operations Dashboard**, showing that metric counts are backed by live PoC transactions rather than static fixtures.

### Step 1: Create a Fresh, Clean Product Catalog & Inventory
On your local machine or host VM terminal, use the provided script to register a new SKU, initialize its inventory, and set its price USD value:

```bash
# 1. Fetch a token for the administrator
TOKEN=$(curl -s -d "client_id=shopsphere-frontend" -d "username=operations@yopmail.com" -d "password=TestPassword@1234" -d "grant_type=password" "http://localhost:8080/realms/shopsphere/protocol/openid-connect/token" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 2. Register a new product
PRODUCT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "sku": "DEMO-PERF-SKU-001",
  "name": "SRE Validation Token",
  "category_id": "f876e8c8-b22e-40d5-b3e1-6a02123ff21f",
  "description": "High durability operational token"
}' http://localhost:8000/api/v1/products | grep -o '"product_id":"[^"]*' | cut -d'"' -f4)

echo "Product Created with ID: ${PRODUCT_ID}"

# 3. Initialize Inventory to 100 units
curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "quantity": 100,
  "reason": "initialization",
  "reference": "SRE Audit"
}' "http://localhost:8000/api/v1/inventory/products/${PRODUCT_ID}/adjust"

# 4. Set Price to USD 49.99
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "amount": 49.99,
  "currency": "USD"
}' "http://localhost:8000/api/v1/products/${PRODUCT_ID}/prices/USD"
```

### Step 2: Register a New Customer Profile
Register a unique test customer inside the Keycloak `shopsphere` realm:
```bash
# Exec into Keycloak and create the user 'demo-customer@test.com'
keycloak_pod=$(kubectl -n shopsphere-platform get pod -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')
kubectl -n shopsphere-platform exec -it "$keycloak_pod" -- bash -c '
  /opt/keycloak/bin/kcadm.sh config credentials --server http://127.0.0.1:8080 --realm master --user admin --password TestPassword@1234
  /opt/keycloak/bin/kcadm.sh create users -r shopsphere -s username=demo-customer@test.com -s enabled=true -s email=demo-customer@test.com -s emailVerified=true -s requiredActions=[]
  /opt/keycloak/bin/kcadm.sh set-password -r shopsphere --username demo-customer@test.com --new-password TestPassword@1234 --temporary=false
  /opt/keycloak/bin/kcadm.sh add-roles -r shopsphere --uusername demo-customer@test.com --rolename customer
'
```

### Step 3: Populate Customer Cart & Execute Checkout
Simulate the customer logging in, populating their shopping cart, and checking out through the API Gateway:

```bash
# 1. Fetch Keycloak Token for the new customer
CUST_TOKEN=$(curl -s -d "client_id=shopsphere-frontend" -d "username=demo-customer@test.com" -d "password=TestPassword@1234" -d "grant_type=password" "http://localhost:8080/realms/shopsphere/protocol/openid-connect/token" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 2. Add product 'DEMO-PERF-SKU-001' to cart (quantity: 2)
curl -s -H "Authorization: Bearer $CUST_TOKEN" -H "Content-Type: application/json" -d "{
  \"product_id\": \"${PRODUCT_ID}\",
  \"quantity\": 2,
  \"currency\": \"USD\"
}" http://localhost:8000/api/v1/carts/me/items

# 3. Process Checkout with Idempotency Key
curl -s -H "Authorization: Bearer $CUST_TOKEN" -H "Content-Type: application/json" -H "Idempotency-Key: demo-transaction-key-001" -d '{}' http://localhost:8000/api/v1/orders/checkout
```

### Step 4: Open and Verify the Executive Dashboard
Query the `/operations/dashboard` endpoint via API Gateway:
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/operations/dashboard
```

**Expected Real-Time Output Metrics:**
*   **Orders Processed:** Increments dynamically by 1 (e.g. `7` orders processed).
*   **Simulated Revenue:** Increases by exactly **`USD 99.9800`** ($49.99 \times 2$ units).
*   **Customer Registrations:** Successfully counts the newly registered `demo-customer@test.com`.
*   **Products Available:** Product and Category counts reflect the fresh catalogue registration.
*   **Inventory Status:** Authoritative inventory stats report the correct on-hand ($100$ units) and reserved ($2$ units) quantities.

---

## Demo B — Full Request Observability

This demo showcases how SREs track a single transaction end-to-end as it traverses multiple decoupled microservices under the cluster topology.

```
┌─────────────────┐      ┌─────────────┐      ┌───────────────┐      ┌───────────────────┐
│  demo-customer  ├─────►│ api-gateway ├─────►│ order-service ├─────►│ catalogue-service │
└─────────────────┘      └─────────────┘      └───────────────┘      └───────────────────┘
```

### 1. Unified Business Correlation (Correlation ID)
Every request entering the platform is assigned a unique `correlation_id` by the API Gateway.
*   **Log Verification (Loki):** Open Grafana and query the Loki data stream `{namespace="shopsphere-apps"}`. Find the `correlation_id` label. You will see that **every log entry** printed by the gateway, the order-service, and the catalogue-service during that single checkout transaction carries the exact same UUID.
*   *SRE Explanation:* “The correlation ID gives us business-request correlation across separate container logs, ensuring we can reconstruct the exact user journey during incident management.”

### 2. Distributed Technical Context (OpenTelemetry Tracing)
*   **Span Propagation:** The API Gateway injects W3C `traceparent` headers into the HTTP request. The downstream `order-service` extracts this, creates children spans, and forwards it to `catalogue-service`.
*   **OpenTelemetry Collector logs:** View the OTEL Collector logs to confirm receipt of active trace spans:
    ```bash
    kubectl -n shopsphere-monitoring logs -l app.kubernetes.io/name=opentelemetry-collector --tail=50
    ```
*   *SRE Explanation:* “OpenTelemetry trace context provides distributed technical trace correlation, mapping exact function call durations and networking latencies across decoupled cluster services.”

---

## Demo C — Failure & Recovery (Self-Healing Validation)

This demo demonstrates how the platform monitors, detects, and gracefully handles severe service failures, and how the Kubernetes infrastructure self-heals.

### Step 1: Simulate a Critical Service Outage
Surgically scale the `order-service` deployment to `0` replicas, simulating a pod crash:
```bash
kubectl -n shopsphere-apps scale deployment/order-service --replicas=0
```

### Step 2: Observe the Observability Pipeline Reactions

#### A. Prometheus Target Unhealthy
Prometheus immediately fails to scrape the pod and marks the target as `DOWN` (0/1 instances):
```bash
# Query active targets status
curl -s http://localhost:9090/api/v1/targets | grep -A 2 '"job":"shopsphere-applications"'
```

#### B. Grafana Service Degraded
Pre-configured alerts on the operations dashboard flag `up{service="order-service"} = 0`. The golden signals panel reflects a spike in HTTP `504 Gateway Timeout` errors.

#### C. Executive Dashboard Degradation
Query the operations dashboard. Notice that the dashboard **does not crash** or return generic errors. It gracefully returns partial health data, marking `order-service` as `unreachable` with status `unknown` while other services remain healthy:
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/operations/dashboard
```

#### D. Centralized Logs Ingestion
Loki streams show the API Gateway log-recording downstream `ConnectError` and `upstream_timeout` exceptions as it attempts to forward checkout traffic.

---

### Step 3: Trigger the Self-Healing Recovery
Restore the service by re-scaling the deployment:
```bash
kubectl -n shopsphere-apps scale deployment/order-service --replicas=1
```

**Expected Outcome:**
1.  Kubernetes instantly schedules and restarts the pod.
2.  Prometheus detects the target has returned to `UP` state inside the next scrape cycle.
3.  The API Gateway automatically resumes proxying traffic to the service.
4.  The Executive Operations Dashboard dynamically recovers to 100% healthy status.
