# Requirements Traceability Matrix

This matrix maps examination requirements to implementation ownership, executable interfaces, evidence, demonstrations, and current status. Status is based on repository contents and validation performed against the current PoC environment.

---

## 1. Status Definitions

*   **Implemented** — executable source or configuration exists.
*   **Unit Validated** — isolated backend or frontend behavior tests executed successfully.
*   **Integration Validated** — the specifically stated multi-component flow executed successfully.
*   **Platform Validated** — deployment, manifest, dependency, or configuration checks executed successfully inside the Kubernetes cluster.
*   **End-to-End Validated** — an authenticated user-facing flow executed successfully through its real application boundaries in the cluster.
*   **Pending / Not Verified** — implementation may exist, but no successful evidence exists for the stated boundary.

---

## 2. Customer Identity & Account Management

| Requirement | Owning Service / Component | API / Workflow | Automated Testing / Validation | Evidence Status |
| --- | --- | --- | --- | --- |
| **Register New Customers** | `customer-service` & Keycloak | React `/register` redirects to Keycloak OIDC Flow with PKCE. Idempotently provisions profile in `customer_db` on successful login. | Tested via `test_profile_provisioning.py` and frontend auth tests. Deployed profile sync validated. | **Implemented; Unit Validated** |
| **Secure Authentication** | Keycloak, API Gateway | OIDC Authorization Code Flow with PKCE. API Gateway verifies RS256 JWT signature, issuer, audience, and scopes. | `test_customer_api.py` and gateway proxy tests pass. Live Keycloak client policies checked. | **Implemented; Unit Validated** |
| **Secure Password Management** | Keycloak | Password entry, hash complexity, and lockout policies occur only on Keycloak-hosted pages. `customer_db` has no credential fields. | Verified via `check-keycloak.sh` validating password length, complexity, history, and lockout thresholds. | **Platform Validated** |
| **Manage Customer Profiles** | `customer-service` | `GET/PATCH /api/v1/profile` reads/updates profile details using validated JWT subject context. | Checked in `test_customer_api.py` and frontend landing page tests. | **Implemented; Unit Validated** |
| **Maintain Customer Addresses** | `customer-service` | `POST/GET/PATCH/DELETE /api/v1/customers/me/addresses` adds, lists, updates, and deletes addresses. | Frontend address tests pass. | **Implemented; Unit Validated** |
| **Role-Based Access Control** | Keycloak & `customer-service` | Roles `customer`, `support`, and `operations_admin` are mapped. Support is read-only; admin controls status. | Keycloak composite role configuration and token roles evaluation checked. | **Platform Validated** |
| **Account Audit History** | `customer-service` | Domain changes write append-only records to `customer_db` history tables. Support reads support paths. | Database schema constraints and migration head checked. | **Implemented; Unit Validated** |
| **Customer Activity Logs** | `customer-service` | `/customers/me/activity` merges domain audit with Keycloak audit logs. | Client event mappings and Keycloak log audit settings verified. | **Implemented** |

---

## 3. Product Catalogue & Inventory Management

| Requirement | Owning Service / Component | API / Workflow | Automated Testing / Validation | Evidence Status |
| --- | --- | --- | --- | --- |
| **Register Products** | `catalogue-service` | `POST /api/v1/products` registers a new product and SKU. Commits product-created event to the PostgreSQL outbox. | Covered by 60 passing Pytest unit/API tests and integration suites. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Manage Categories** | `catalogue-service` | `POST/GET/PATCH /api/v1/categories` registers hierarchy and slug relations, rejecting cycle parent loops. | Unit tests validating parent edit loops passed successfully. | **Implemented; Unit Validated; Platform Validated; End-to-End Validated** |
| **Manage Inventory Levels** | `catalogue-service` | Initializes or adjusts hand quantities, ensuring reserved balances do not exceed on-hand stock. | Adjustments and stale-version concurrent locks tested and passed. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Track Product Availability** | `catalogue-service` | `GET /api/v1/inventory/products/{product_id}/availability` returns derived `on_hand - reserved` balance using Redis read caching. | Pytest derivation tests and Redis cache invalidation tests passed. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Search Products** | `catalogue-service` | `GET /api/v1/products` filters by text, SKU, category slug, and visibility status. | Evaluated with client searches and cache-aside query tests. | **Implemented; Unit Validated; Platform Validated; End-to-End Validated** |
| **Manage Pricing Info** | `catalogue-service` | `PUT /api/v1/products/{id}/prices/{currency}` overrides prices with Decimal precision, storing price outbox events. | USD decimal validation and price integration tests passed. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Record Inventory Updates** | `catalogue-service` | Append-only `inventory_movements` triggered by all stock adjustments. | Invariants, triggers, and outbox publisher checks passed. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Display Inventory Statistics** | `catalogue-service` | `GET /api/v1/inventory/statistics` calculates totals and low-stock categories. | Checked on-hand summaries and analytics integrations. | **Implemented; Unit Validated; Integration Validated; Platform Validated** |

---

## 4. Enterprise Order Processing

| Requirement | Owning Service / Component | API / Workflow | Automated Testing / Validation | Evidence Status |
| --- | --- | --- | --- | --- |
| **Create Shopping Carts** | `order-service` | `GET/POST/PATCH/DELETE /api/v1/carts/me` manages cart items and lines per user subject. | Checked with 46 passing Pytest cases and frontend Vitest component suites. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Validate Product Availability** | `catalogue-service` & `order-service` | Cart checkout requests synchronous inventory reservations in catalogue-service. | Handled via transaction locks and insufficient stock compensation tests. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Process Orders** | `order-service` | `POST /api/v1/orders/checkout` processes cart into CONFIRMED order using transactional outbox and Kafka. | Idempotency, retry keys, and outbox schema validations passed. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Generate Order Confirmations** | `order-service` | Checkout returns a CONFIRMED order payload with unique number and immutable items snapshot. | Tested in list/detail APIs and E2E Happy Path runs. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Calculate Order Totals** | `order-service` | Evaluates authoritative quotation total using database `NUMERIC` types, blocking browser manipulation. | Verified Decimal precision and stale price change recalculations. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Track Order Status** | `order-service` | Tracks status history (CONFIRMED, PROCESSING, FULFILLED, CANCELLED) with append-only logs. | State machine transition policies and cancellations verified. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Maintain Complete History** | `order-service` | `GET /api/v1/orders/me` lists scoped historical orders and statuses. | IDOR prevention, support read-only, and list pagination verified. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| **Produce Transaction Audits** | `order-service` | `GET /api/v1/orders/me/{id}/audit` retrieves audit actions, correlations, and outbox logs. | Checked append-only schemas, database triggers, and outbox recovery. | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |

---

## 5. Executive Operations & Dashboard (Wired End-to-End)

| Requirement | Implementation Component | API / Workflow | SRE Verification / Evidence | Evidence Status |
| --- | --- | --- | --- | --- |
| **Orders Processed** | `analytics-service` & React UI | `GET /api/v1/operations/dashboard` bound directly to frontend KPI cards. | Real-time counts mapped to Postgres database states; fully integrated in React SPA. | **End-to-End Validated** |
| **Simulated Revenue** | `analytics-service` & React UI | Sums confirmed order totals in USD with "Simulated" labeling. | Verified price and currency string mappings to Pydantic and React; fully integrated in React SPA. | **End-to-End Validated** |
| **Customer Registrations** | `analytics-service` & React UI | Counts Keycloak-provisioned customer profile registrations. | Fully synchronized from Keycloak database and bound to UI; verified in React SPA. | **End-to-End Validated** |
| **Product Availability** | `analytics-service` & React UI | Counts available items across active ranges. | Direct mapping from catalogue stats; fully integrated in React SPA. | **End-to-End Validated** |
| **Inventory Status** | `analytics-service` & React UI | Displays low-stock and out-of-stock item indicators. | Monitored dynamically via Postgres and Redis; fully integrated in React SPA. | **End-to-End Validated** |
| **Order Fulfilment Status** | `analytics-service` & React UI | Displays distribution of processing vs cancelled orders. | Dynamically aggregated from order history; fully integrated in React SPA. | **End-to-End Validated** |
| **System Performance** | `analytics-service` & React UI | Displays Golden Signals (API Availability, request/error rate %). | Safely parsed from Prometheus metric matrices; fully integrated in React SPA. | **End-to-End Validated** |
| **Application Health** | `analytics-service` & React UI | Displays service-health indicators with appropriate tones (positive, warning, critical). | Real-time health states evaluated dynamically; fully integrated in React SPA. | **End-to-End Validated** |
| **Business KPIs** | `analytics-service` & React UI | Combined business dashboard with partial-failure resilience. | Safe API recovery under network partitions; fully integrated in React SPA. | **End-to-End Validated** |
| **Operational Alerts** | `analytics-service` & React UI | Renders active, firing operational alerts from Prometheus. | Checked via query integration and rule evaluations; fully integrated in React SPA. | **End-to-End Validated** |

---

## 6. SRE Observability & Security

| Requirement / Component | Deployed State | Monitored Attributes / Indicators | SRE Verification | Evidence Status |
| --- | --- | --- | --- | --- |
| **Prometheus** | Single-node k8s deployment | Core CPU, Memory, HTTP Golden Signals, Scraper targets | Active target scraping for `shopsphere-applications` job verified. | **Platform Validated** |
| **Grafana** | Provisioned dashboard workloads | Host metrics, connection rates, cluster performance | 4 operations dashboards pre-configured with read-only datasources. | **Platform Validated** |
| **Loki & Promtail** | Promtail DaemonSet + Loki | Log streams parsed recursively from `/var/log/pods` | Correlation IDs and trace IDs successfully tracked in logs. | **Platform Validated** |
| **OpenTelemetry Collector** | OTLP metrics & trace receiver | Context propagation from API Gateway to downstream services | OTLP receiver active on ports 4317/4318; visualization backend not deployed. | **Implemented** |
| **Wazuh Monitoring** | Manager & DaemonSet Agent | Sandboxed file system integrity, active-response alerts | Touch FIM event inside agent `/etc/` correctly registered Level 7 anomaly. | **Platform Validated** |

---

## 7. DevSecOps Quality Gates

| Quality Gate Stage | Tool / Utility | Monorepo Ownership | Outcome / Validation | Evidence Status |
| --- | --- | --- | --- | --- |
| **Python Styling** | `Black` | All 5 microservices | Standard format checks enforced onapp and tests. | **Platform Validated** |
| **Python Linting** | `Ruff` | All 5 microservices | JSON reports archived under `test-results/lint/`. | **Platform Validated** |
| **Automated Testing** | `Pytest` & `Vitest` | All services + React | 100+ tests pass with separate JUnit output. | **Integration Validated** |
| **Python Security** | `Bandit` | Core microservices | Recursively scans for code flaws (e.g. binding 0.0.0.0). | **Platform Validated** |
| **Static Code Audit** | `Semgrep` | Root workspace | Analyzes monorepo patterns using Docker image. | **Platform Validated** |
| **Vulnerability Scan** | `Trivy` | Filesystem & Images | Trivy FS and individual service image scans verified. | **Platform Validated** |
| **Policy as Code** | `Open Policy Agent` | `platform/security/rego` | `security.rego` prevents privileged pods and root execution. | **Platform Validated** |
| **Deployment Guard** | `Kustomize` | Platform overlays | Overrides tags with `ci-${BUILD_NUMBER}` for rollouts. | **Platform Validated** |
| **Smoke Testing** | `curl` / bash | Deployed platform | Gateway transactions verified after automated deployment. | **Integration Validated** |
