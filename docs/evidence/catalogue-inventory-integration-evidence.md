# Product Catalogue and Inventory Evidence Assessment

## Evidence rules

This assessment distinguishes source implementation, unit/component execution,
service/platform integration, deployment health, and an authenticated user journey.
The current catalogue integration JUnit file contains **11 passed tests**, zero failures,
zero errors and zero skips. The suite was explicitly enabled against the PoC and used
temporary synthetic identities and ephemeral test clients that were removed afterward.

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
| Register products | Product application/repository, React product form, Gateway route | `/products/new` → Gateway `POST /api/v1/products` → catalogue-service | `products`; unique immutable normalized SKU; product-created outbox row in same transaction | `operations_admin` write; customer/support denied | Backend registration/duplicate/RBAC/event tests and frontend permission/form tests passed | Catalogue/Gateway manifests passed; both workloads Ready/ClusterIP; live outbox row was broker-acknowledged | Authenticated administrator registered synthetic SKU `MANUAL-20260813-001`; customer subsequently found and opened it | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| Manage product categories | Category application/repository and React category page | Gateway category list/create/update routes | `product_categories`; unique slug, active flag and validated optional parent | Governed reads; `operations_admin` writes | Backend create/update/duplicate/cycle/RBAC, Gateway and frontend tests passed | PostgreSQL/catalogue/Gateway validated | Authenticated administrator created the category used by the live product; update/parent editing remains automated-test-only | **Implemented; Unit Validated; Platform Validated; category creation End-to-End Validated; update/parent End-to-End Pending / Not Verified** |
| Manage inventory levels | Inventory service/repository and adjustment page | Initialize or confirm adjustment through Gateway inventory commands | Versioned `inventory_items`; database balance constraints; movement and outbox commit atomically | Customer availability-only; support read-only; `operations_admin` mutates | Initialization, increase/decrease, invariant, concurrency, idempotency, RBAC, Gateway and frontend tests passed | PostgreSQL/Redis/Kafka/catalogue validated; live inventory events broker-acknowledged | Administrator initialized 5 units, a `-10` attempt was rejected without changing stock, and `+20` resulted in 25 | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| Track product availability | Derived availability API/cache/UI | Gateway `GET /api/v1/inventory/products/{id}/availability` | Derived from `inventory_items`; short-lived Redis snapshot only | Governed read with customer-safe response | Derivation, state, visibility, TTL, invalidation, fallback, Gateway and frontend tests passed | Redis/catalogue workloads Ready; persisted balance independently verified as on-hand 25, reserved 0, available 25 | Customer saw safe availability change from 5 to 25 after adjustment; operational fields remained restricted | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| Search products | PostgreSQL query repository, cached search and React filters | Gateway `GET /api/v1/products` with query/filter/sort/page parameters | PostgreSQL product/category data authoritative; Redis query result disposable | Customer active/searchable visibility; support/admin operational reads | Backend search/filter/sort/page/visibility/cache, Gateway forwarding and frontend tests passed | Catalogue/Redis/Gateway manifests and workloads validated | Administrator and customer found the live product by its governed catalogue workflow; customer could open but not edit it | **Implemented; Unit Validated; Platform Validated; End-to-End Validated** |
| Manage pricing information | Pricing service/repository and pricing page | Read prices; admin Gateway `PUT /api/v1/products/{id}/prices/{currency}` | `product_prices` uses `NUMERIC(19,4)`, effective history; price event stored in outbox transaction | Governed current reads; support/admin history; admin writes | Precision/history/validation/RBAC/cache/event, Gateway and frontend tests passed | Live `catalogue.price.changed.v1` outbox row reached `published` after one attempt | Administrator set `USD 49.9900`; customer viewed the same current price without edit controls | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| Record inventory updates | Immutable movement repository/API/UI and outbox | Accepted stock command creates movement; operational users page movement history | Append-only `inventory_movements`; actor, reason, deltas, prior/resulting balances, correlation and idempotency; trigger rejects mutation | Support/admin read; admin causes current movement types | Movement, immutability, retry/concurrency/RBAC/event, Gateway and frontend tests passed | Two live `inventory.adjusted.v1` rows reached `published` after one attempt each | Movement UI showed initialization and `+20` receipt; customer mutation returned 403; rejected negative-stock command created no movement | **Implemented; Unit Validated; Integration Validated; Platform Validated; End-to-End Validated** |
| Display inventory statistics | Statistics query/cache/API and React statistics page | Support/admin Gateway `GET /api/v1/inventory/statistics` | Calculated from authoritative `inventory_items`; Redis snapshot is bounded/disposable | `support` and `operations_admin`; customer denied | Calculation/RBAC/cache, Gateway and frontend rendering tests passed | Catalogue/PostgreSQL/Redis/Gateway manifests and workloads validated | Authenticated support request through the Gateway returned persisted statistics; browser statistics page was not manually exercised | **Implemented; Unit Validated; Integration Validated; Platform Validated; browser End-to-End Pending / Not Verified** |

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
- Catalogue live integration suite: **11 passed in 79.09 seconds**, zero failed, zero
  errors and zero skipped. JUnit evidence is retained at
  `test-results/integration/catalogue-inventory.xml`.
- The live suite validated authenticated Gateway product/category/search/pricing and
  inventory flows, RBAC, missing/invalid/expired tokens, inventory statistics, cache
  invalidation and hit/miss behavior, versioned event publication, Redis outage fallback,
  and Kafka outage/outbox recovery.
- Redis and Kafka were restored and passed their repository status checks. Catalogue-service
  and API Gateway were Ready afterward. All temporary Keycloak users and clients were removed.

## Authenticated manual validation evidence

On 2026-08-13, the operator completed the documented browser workflow through React,
Keycloak, API Gateway and catalogue-service with separate `operations_admin` and
`customer` sessions. The flow created a synthetic active/searchable product with SKU
`MANUAL-20260813-001`, assigned `USD 49.9900`, initialized 5 units, rejected a `-10`
adjustment, accepted a `+20` receipt, displayed 25 available units, retained two movement
records, and returned HTTP 403 for a customer inventory mutation attempt. Customer UI
access remained read-only.

A subsequent read-only PostgreSQL check independently verified product UUID
`aa334224-a863-4398-9cfa-485eb94b20cf` as active/searchable with on-hand 25, reserved 0,
available 25, inventory version 2 and two movements. Its outbox contained four rows, all
`published` after one attempt: `catalogue.product.created.v1`,
`catalogue.price.changed.v1`, and two `inventory.adjusted.v1` events. The inventory events
use the inventory-item UUID as `aggregate_id`; they were located through the safe
`payload.product_id` reference. Inventory statistics were not exercised in this manual
browser journey, but the later authenticated live integration suite successfully exercised
the statistics API through the Gateway with a support identity.

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
