# Product Catalogue and Inventory Evidence Assessment

## Evidence rules

This assessment distinguishes source implementation, unit/component execution,
service/platform integration, deployment health, and an authenticated user journey.
The current catalogue integration JUnit file contains **11 skipped tests**. It proves
collection and safe opt-in behavior only; none of those skips is recorded as a pass.

Evidence states mean:

- **Implemented** — executable source/configuration exists.
- **Unit Validated** — isolated backend or frontend behavior tests executed successfully.
- **Integration Validated** — a stated multi-component scenario executed successfully.
- **Platform Validated** — manifests or current internal workloads/dependencies were checked.
- **End-to-End Validated** — the authenticated browser-to-Gateway-to-service workflow executed.
- **Pending / Not Verified** — the stated boundary has no successful retained evidence.

## Examination requirements

| Requirement | Implementation component | API/user workflow | Persistence model | Authorization | Automated tests | Platform validation | End-to-end validation | Current evidence status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Register products | Product application/repository, React product form, Gateway route | `/products/new` → Gateway `POST /api/v1/products` → catalogue-service | `products`; unique immutable normalized SKU; product-created outbox row in same transaction | `operations_admin` write; customer/support denied | Backend registration/duplicate/RBAC/event tests and frontend permission/form tests passed | Catalogue/Gateway manifests passed; both workloads Ready/ClusterIP; earlier internal smoke created a simulated product and published its event | Live suite skipped; authenticated browser journey not run | **Implemented; Unit Validated; Platform Validated; internal create/event Integration Validated; End-to-End Pending / Not Verified** |
| Manage product categories | Category application/repository and React category page | Gateway category list/create/update routes | `product_categories`; unique slug, active flag and validated optional parent | Governed reads; `operations_admin` writes | Backend create/update/duplicate/cycle/RBAC, Gateway and frontend tests passed | PostgreSQL/catalogue/Gateway validated; earlier internal smoke created one category | Live suite skipped; no authenticated update/parent journey | **Implemented; Unit Validated; Platform Validated; create-only integration evidence; End-to-End Pending / Not Verified** |
| Manage inventory levels | Inventory service/repository and adjustment page | Initialize or confirm adjustment through Gateway inventory commands | Versioned `inventory_items`; database balance constraints; movement and outbox commit atomically | Customer availability-only; support read-only; `operations_admin` mutates | Initialization, increase/decrease, invariant, concurrency, idempotency, RBAC, Gateway and frontend tests passed | PostgreSQL/Redis/Kafka/catalogue validated; earlier smoke initialized/adjusted stock | Live suite skipped; no authenticated UI journey | **Implemented; Unit Validated; Platform Validated; internal stock Integration Validated; End-to-End Pending / Not Verified** |
| Track product availability | Derived availability API/cache/UI | Gateway `GET /api/v1/inventory/products/{id}/availability` | Derived from `inventory_items`; short-lived Redis snapshot only | Governed read with customer-safe response | Derivation, state, visibility, TTL, invalidation, fallback, Gateway and frontend tests passed | Redis/catalogue workloads Ready and manifest checks passed; controlled Redis fallback was previously validated | Live suite skipped | **Implemented; Unit Validated; Platform Validated; End-to-End Pending / Not Verified** |
| Search products | PostgreSQL query repository, cached search and React filters | Gateway `GET /api/v1/products` with query/filter/sort/page parameters | PostgreSQL product/category data authoritative; Redis query result disposable | Customer active/searchable visibility; support/admin operational reads | Backend search/filter/sort/page/visibility/cache, Gateway forwarding and frontend tests passed | Catalogue/Redis/Gateway manifests and workloads validated | Live suite skipped | **Implemented; Unit Validated; Platform Validated; End-to-End Pending / Not Verified** |
| Manage pricing information | Pricing service/repository and pricing page | Read prices; admin Gateway `PUT /api/v1/products/{id}/prices/{currency}` | `product_prices` uses `NUMERIC(19,4)`, effective history; price event stored in outbox transaction | Governed current reads; support/admin history; admin writes | Precision/history/validation/RBAC/cache/event, Gateway and frontend tests passed | PostgreSQL/Redis/Kafka/catalogue/Gateway validated; earlier smoke published a price change | Live suite skipped | **Implemented; Unit Validated; Platform Validated; internal price-change Integration Validated; End-to-End Pending / Not Verified** |
| Record inventory updates | Immutable movement repository/API/UI and outbox | Accepted stock command creates movement; operational users page movement history | Append-only `inventory_movements`; actor, reason, deltas, prior/resulting balances, correlation and idempotency; trigger rejects mutation | Support/admin read; admin causes current movement types | Movement, immutability, retry/concurrency/RBAC/event, Gateway and frontend tests passed | PostgreSQL trigger/outbox/Kafka validated; earlier smoke published adjustment and threshold facts | Live suite skipped; movement UI not exercised against live Gateway | **Implemented; Unit Validated; Platform Validated; internal movement/event Integration Validated; End-to-End Pending / Not Verified** |
| Display inventory statistics | Statistics query/cache/API and React statistics page | Support/admin Gateway `GET /api/v1/inventory/statistics` | Calculated from authoritative `inventory_items`; Redis snapshot is bounded/disposable | `support` and `operations_admin`; customer denied | Calculation/RBAC/cache, Gateway and frontend rendering tests passed | Catalogue/PostgreSQL/Redis/Gateway manifests and workloads validated | Live suite skipped | **Implemented; Unit Validated; Platform Validated; End-to-End Pending / Not Verified** |

## Executed automated and platform evidence

- Catalogue-service: **48 tests passed**, 80% aggregate statement coverage.
- Focused React catalogue/inventory suite: **6 tests passed**.
- Ruff: passed with zero findings; Bandit over catalogue application code: zero findings.
- Black: 46 catalogue Python files passed individual checks.
- Alembic: one connected chain of three revisions, base `001_product_catalogue`,
  head `003_domain_event_outbox`; PostgreSQL offline upgrade SQL compiled.
- Docker: `shopsphere/catalogue-service:ci-validation` built successfully.
- Non-destructive manifest validation passed for Kubernetes base, PostgreSQL,
  catalogue-service, API Gateway, Redis and single-broker KRaft Kafka resources.
- Read-only topology checks observed one Ready API Gateway, catalogue-service, Redis
  and Kafka workload. API Gateway and catalogue-service Services were ClusterIP.
- Earlier retained platform evidence records a PostgreSQL migration round trip,
  authenticated Redis fallback, internal simulated catalogue mutations, eight published
  outbox rows and all six event types consumed from the PoC Kafka broker.
- Catalogue live integration suite: **11 skipped**, zero passed, zero failed because the
  protected execution opt-in/configuration was not supplied.

## Data and event authority

PostgreSQL is the source of truth for products, categories, prices, inventory balances,
movements, statistics inputs and outbox state. Redis is a performance optimization only:
entries are namespaced, expire, are invalidated after committed changes, and may be
discarded or bypassed. Kafka transports asynchronous domain facts and is not consulted
to decide whether a catalogue or stock transaction committed.

The aggregate/movement change and outbox event intent commit in one PostgreSQL
transaction. The relay publishes committed rows and marks them published only after
Kafka acknowledgement. Delivery is **at least once**: acknowledgement loss can cause a
duplicate with the same `event_id`, so consumers must be idempotent. Kafka unavailability
leaves retryable outbox rows and does not invalidate the authoritative database change.
Ordering is per aggregate key within a topic partition; cross-topic ordering is not
guaranteed. No event consumer or schema registry is implemented.

## PoC and production boundary

The PoC has one PostgreSQL instance/PVC, one ephemeral Redis instance, one combined
KRaft Kafka broker/controller with one retained PVC, one kind node, and one physical GCP
VM. It has no host-level high availability. Multiple pods on that node do not remove the
node or VM failure domain.

Production should use managed regional/high-availability PostgreSQL with encrypted
automated backups, PITR and tested failover; replicated cross-zone Redis with TLS,
authentication and automatic failover; and managed or multi-broker Kafka across zones
with replication, TLS, ACLs and schema governance. Run workloads across multiple
Kubernetes nodes/zones, add measured horizontal autoscaling, private connectivity,
workload identity, external secret management, enforced network policy, controlled
ingress/egress, monitoring and tested disaster recovery.
