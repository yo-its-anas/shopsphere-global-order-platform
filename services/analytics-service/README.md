# Analytics Service

Read-only FastAPI aggregation boundary for the ShopSphere Executive Business Operations Dashboard. Customer, Catalogue/Inventory, and Order services remain authoritative; this service neither owns their transactional data nor queries their databases.

---

## 1. Verified Executable APIs

All business endpoints require an authorized Bearer token from Keycloak (`operations_admin` or `support` roles) and return real-time metrics with partial failure metadata.

| Endpoint | Data | Roles Required | Evidence Status |
| --- | --- | --- | --- |
| `GET /api/v1/operations/dashboard` | Combined service health, alerts, and performance metrics | `operations_admin` | **Platform Validated** |
| `GET /api/v1/dashboard/summary` | General business aggregates | `operations_admin` | **Platform Validated** |
| `GET /api/v1/dashboard/orders` | Orders status trends and revenue | `operations_admin` | **Platform Validated** |
| `GET /api/v1/dashboard/inventory` | Inventory balances and low stock levels | `support`, `operations_admin` | **Platform Validated** |
| `GET /api/v1/dashboard/customers` | Customer registrations count | `support`, `operations_admin` | **Platform Validated** |

---

## 2. Metrics Mapping & Sources (Formal Validation)

To ensure the executive dashboard remains robust and correct, we map the following core metrics directly to their authoritative upstream owners:

### 2.1 Orders Processed & Simulated Revenue
*   **Authoritative Owner:** `order-service`
*   **Analytics Implementation:** Queries order-service admin API `/api/v1/admin/orders` to aggregate non-cancelled, confirmed order totals.
*   **Formula:** `Simulated Revenue = sum(confirmed_order_totals) per currency` (labeled simulated because credit settlement is out of scope).

### 2.2 Customer Registrations
*   **Authoritative Owner:** `customer-service`
*   **Analytics Implementation:** Queries customer-service profile provisioning and audit endpoints to count registered profiles.

### 2.3 Product Availability & Inventory Status
*   **Authoritative Owner:** `catalogue-service`
*   **Analytics Implementation:** Queries catalogue-service `/api/v1/inventory/statistics` to retrieve totals for on-hand, low-stock, and out-of-stock items.

### 2.4 System Performance & Application Health
*   **Authoritative Owner:** `Prometheus` (platform scraper)
*   **Analytics Implementation:** Queries the Prometheus API `/api/v1/query` safely to evaluate the `up{job="shopsphere-applications"}` metric and calculate total request rates and HTTP error rates over the last 5 minutes.
*   **Authorization:** The `analytics-service` is granted egress to the `shopsphere-monitoring` namespace. Ingress access is secured via a customized `prometheus-ingress` NetworkPolicy allowing TCP port `9090` from the `shopsphere-apps` namespace.

---

## 3. Resilience and Security

*   **DNS & Routing Security:** Upstream client URLs are strictly bound to cluster DNS variables. Callers cannot pass arbitrary URLs.
*   **Credential Shielding:** Token values are stripped recursively from error responses and never emitted to logs or traces.
*   **Partial Failures Supported:** If an upstream service is down, its values return `null` and the `data_status` returns `partial` (or `unavailable` if all are down), ensuring the API Gateway does not crash.

---

## 4. Local Execution & Validation

To test and run the service locally or execute unit tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
black --check app tests
ruff check app tests
bandit -q -r app
pytest
```
