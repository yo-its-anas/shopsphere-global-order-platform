# Product Catalogue Validation Record

This record covers the implemented Product Catalogue, Inventory, cache-aside, transactional outbox/event producer, internal PoC deployment boundary, API Gateway transport, frontend component validation, authenticated live integration, and the principal manual browser journey. A later controlled Order platform smoke additionally validates the reservation/release participant; event consumers remain outside this evidence. API Gateway is internally deployed; the React frontend is implemented and build-validated but is not deployed in Kubernetes.

## Kafka and outbox validation

The catalogue suite executes 48 tests and includes versioned-envelope, product-created, product-updated, price-changed, inventory-adjusted, low-stock, out-of-stock, acknowledgement-loss duplicate, and broker-unavailable retry behavior. The migration graph and offline PostgreSQL SQL validation report one connected chain with `003_domain_event_outbox` as its head.

The live PoC validation created six governed one-partition topics on the internal Kafka 4.3.1 KRaft broker. A temporary service-account client received only the `operations_admin` role, submitted simulated category/product/update/price/inventory operations, and was deleted immediately afterward. Eight outbox rows for the correlation prefix reached `published`: three catalogue facts, three inventory-adjusted facts, and the low/out-of-stock transition facts. A consumer read all six event types from Kafka and confirmed the documented envelope and safe payload projection. No credential or token was printed. Kafka remained Ready, its client Service remained ClusterIP-only, and `kafka-data-kafka-0` remained Bound.

This evidence does not prove broker failover or high availability. Kafka and the producer share the same kind node and physical VM; the PoC listener is private plaintext without authentication/ACLs, and NetworkPolicy enforcement depends on the CNI.

## Automated results

| Boundary | Validation | Result |
| --- | --- | --- |
| Formatting | Ruff formatter check across `app`, `tests`, and `migrations` | Passed |
| Formatting | Black checked 46 Python files individually | Passed |
| Lint | Ruff | Passed |
| Security static analysis | Bandit over `app` | Passed |
| Service tests | Pytest with signed simulated JWTs and repository-isolated API/domain/cache tests | 48 tests passed; 80% application coverage |
| Persistence contract | SQLAlchemy metadata tests | Passed; price precision, inventory balance/version constraints, idempotency uniqueness, and movement constraints are present |
| Alembic offline | Revision graph and PostgreSQL SQL generation | Passed; three revisions and one head: `003_domain_event_outbox` |
| Alembic PostgreSQL round trip | Upgrade, five-table verification, constraint/trigger execution, downgrade, and re-upgrade against disposable PostgreSQL 16 | Passed |
| Alembic drift | `alembic check` after upgrade against disposable PostgreSQL 16 | Passed; no new upgrade operations detected |
| Container | `docker build --tag shopsphere/catalogue-service:poc services/catalogue-service` | Passed |
| Redis/cache manifests | Kustomize render, client dry run, secret/reference/exposure/security/probe checks | Passed |
| Catalogue workload manifests | Kustomize render, client dry run, dependency/exposure/security/probe checks | Passed |
| Live Redis | Ready authenticated pod and ClusterIP-only Service in `shopsphere-data` | Passed |
| Live catalogue-service | Ready pod, successful database migration init container, health probes, authenticated Redis connectivity, and ClusterIP-only Service | Passed |
| Controlled Redis outage | Redis scaled to zero, catalogue liveness/readiness/info and safe cache miss verified, Redis restored to one Ready replica | Passed |
| API Gateway transport | Fixed Catalogue/Inventory route allow-list, query/pagination/body forwarding, bearer and correlation propagation, normalized timeout/unavailable/protocol failures, safe logging, readiness dependency status, and OpenAPI exposure | Passed in the isolated gateway suite; deployed gateway Ready and live route reached backend authentication |
| Catalogue dependency access | `catalogue_db` identity, authenticated Redis ping, Keycloak JWKS retrieval, Kafka socket connectivity, and outbox acknowledgement | Passed without displaying credentials; eight simulated events reached `published` |
| Frontend catalogue/inventory | Focused Vitest component/route/API-adapter coverage | 6 tests passed; production build passed |
| Live catalogue integration suite | Explicitly enabled authenticated Gateway, RBAC, inventory/statistics, cache and event/recovery scenarios | **11 passed in 79.09 seconds; zero failures, errors or skips** |

The live suite temporarily scaled Redis and Kafka to zero only in their explicitly
authorized recovery tests. Both workloads were restored and passed status checks;
catalogue-service and API Gateway remained Ready afterward. Three synthetic users and
both ephemeral Keycloak test clients were removed. JUnit output is retained at
`test-results/integration/catalogue-inventory.xml`.

Catalogue revisions `001_product_catalogue`, `002_enterprise_inventory`, and `003_domain_event_outbox` are present in the connected migration chain. Earlier deployment evidence confirms the init container applied the catalogue schema without recreating the database, PostgreSQL pod, or persistent volume. Redis runtime credentials exist only in namespace-scoped Kubernetes Secrets and were not displayed.

## Covered behavior

- category create/update, normalized slug uniqueness, parent validation, and cycle rejection;
- product registration/update/deactivation and normalized immutable SKU uniqueness;
- active/searchable customer visibility and broader read-only support visibility;
- immediate effective decimal price replacement with retained history;
- supported-currency and invalid monetary-value rejection;
- customer/support write rejection and operations-administrator mutation access;
- text/SKU/category/status search, sorting, pagination, and invalid query validation;
- missing/invalid authentication, invalid UUIDs, mass-assignment rejection, OpenAPI paths, and database readiness failure response.
- stock initialization, receipt, damage, manual correction, and derived availability;
- non-negative/reserved-within-on-hand invariants and customer-safe availability;
- idempotent movement commands, stale concurrent-writer rejection, and append-only history;
- customer/support/operations authorization boundaries and inactive-product hiding;
- calculated in-stock/low-stock/out-of-stock and unit-total statistics;
- PostgreSQL rejection of movement update/delete and negative on-hand balances.
- cache miss/hit, TTL expiry, namespaced and hashed keys, product/search invalidation, price invalidation, availability invalidation, malformed payload eviction, and Redis outage fallback.

## Evidence limitations

API/domain/cache tests use in-memory repository and cache contract implementations for deterministic behavior. Redis adapter tests cover TTL forwarding, malformed JSON, and Redis exceptions. The reservation migration `004_inventory_reservations` is applied to the live PoC Catalogue database. Reservation routes intentionally remain internal. The dedicated `order_service` identity was accepted by Catalogue, and a simulated Gateway checkout followed by cancellation reserved and released stock while related Order outbox events reached `published`. This adds Platform/Integration validation for reserve/release; automatic expiry, atomic multi-product reservation and browser evidence remain Pending / Not Verified. API Gateway, Redis, Kafka, PostgreSQL, catalogue-service and order-service run on the same kind node and are not highly available.
