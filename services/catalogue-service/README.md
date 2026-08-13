# Catalogue Service

FastAPI service for Product Catalogue categories, product lifecycle, PostgreSQL search, effective pricing, transactional inventory management, optional Redis read caching, and recoverable Kafka event production. Order reservations and event consumers are not implemented. The separate API Gateway exposes an explicit transport mapping to these service routes without taking ownership of catalogue business logic.

The service follows the [Product Catalogue and Inventory domain design](../../docs/architecture/catalogue-inventory-domain-design.md). Catalogue and Inventory remain separate bounded contexts even though both are allocated to this service for the PoC.

## Implemented API

All business routes require a Keycloak-compatible bearer token for the `shopsphere-api` audience.

| Method | Path | Authorized roles |
| --- | --- | --- |
| `POST` | `/api/v1/categories` | `operations_admin` |
| `GET` | `/api/v1/categories` | `customer`, `support`, `operations_admin` |
| `GET` | `/api/v1/categories/{category_id}` | `customer`, `support`, `operations_admin` |
| `PATCH` | `/api/v1/categories/{category_id}` | `operations_admin` |
| `POST` | `/api/v1/products` | `operations_admin` |
| `GET` | `/api/v1/products` | `customer`, `support`, `operations_admin` |
| `GET` | `/api/v1/products/{product_id}` | `customer`, `support`, `operations_admin` |
| `PATCH` | `/api/v1/products/{product_id}` | `operations_admin` |
| `POST` | `/api/v1/products/{product_id}/deactivate` | `operations_admin` |
| `GET` | `/api/v1/products/{product_id}/prices` | `customer`, `support`, `operations_admin` |
| `PUT` | `/api/v1/products/{product_id}/prices/{currency_code}` | `operations_admin` |
| `GET` | `/api/v1/inventory/products/{product_id}/availability` | `customer`, `support`, `operations_admin` |
| `GET` | `/api/v1/inventory/products/{product_id}` | `support`, `operations_admin` |
| `POST` | `/api/v1/inventory/products/{product_id}/initialize` | `operations_admin` |
| `POST` | `/api/v1/inventory/products/{product_id}/adjustments` | `operations_admin` |
| `PATCH` | `/api/v1/inventory/products/{product_id}/settings` | `operations_admin` |
| `GET` | `/api/v1/inventory/products/{product_id}/movements` | `support`, `operations_admin` |
| `GET` | `/api/v1/inventory` | `support`, `operations_admin` |
| `GET` | `/api/v1/inventory/statistics` | `support`, `operations_admin` |

Customers see only active, searchable products in active categories and current active prices. Support can read inactive operational records and pricing history but cannot modify catalogue state. `operations_admin` owns all mutations. SKU is immutable after registration and unique after trim/uppercase normalization. Category slug is unique after trim/lowercase normalization.

`GET /api/v1/products` supports `query`, `sku`, `category_id`, `status`, `offset`, `limit`, `sort_by`, and `sort_direction`. PostgreSQL `ILIKE` search covers product name, SKU, and description. Customers cannot use status filters to reveal inactive records.

Prices use Python `Decimal` and PostgreSQL `NUMERIC(19,4)`. A price update is immediately effective: it closes the previous active record for the product/currency and appends a new active record. `include_history=true` is restricted to support and operations roles. The supported ISO currency subset is controlled by `SUPPORTED_CURRENCIES`.

Inventory uses one `PRIMARY` PoC location per product. `quantity_available` is always derived as `quantity_on_hand - quantity_reserved`; it is never accepted as input. PostgreSQL constraints enforce non-negative balances and prevent reserved stock from exceeding on-hand stock. Initialization and adjustments require a safe reason and idempotency key, record the verified actor and request correlation ID, and append a movement in the same transaction as the balance change.

Stock adjustments use `SELECT ... FOR UPDATE` and an atomic version predicate to prevent lost updates. Callers may provide `expected_version`; a stale version returns `409`. `STOCK_RECEIPT` must increase stock, `DAMAGE` must decrease it, and manual adjustment/correction deltas must be non-zero. Movement updates and deletes are rejected by a PostgreSQL trigger. Reservation, release, and fulfilment types are schema-compatible future interfaces only and cannot be submitted through the current API.

Customer availability responses expose only derived available quantity, state, and timestamp for active/searchable products. Support is read-only and may inspect balances, history, filtering, and calculated statistics. Operations administrators own initialization, adjustments, and reorder-threshold settings.

## Redis cache-aside policy

PostgreSQL remains authoritative for products, categories, prices, inventory balances, movements, and statistics. Redis contains only reconstructable response snapshots for category reads, product details/search, current prices, safe availability, inventory lists, and inventory statistics.

Keys use the `shopsphere:catalogue:v1:<environment>` namespace and role-safe/query-hash suffixes. Default TTLs are 300 seconds for categories, 180 for product details, 60 for searches, 120 for prices, and 15 for availability/inventory snapshots. Availability TTL is capped at 60 seconds by configuration validation.

Reads use cache-aside behavior. Misses, expired entries, malformed JSON/schema data, timeouts, and connection failures fall back to PostgreSQL. Successful catalogue, pricing, and inventory mutations invalidate affected key families after the database transaction commits. Cache hit/miss/outage/invalidation events are structured and contain only the cache family, never tokens, credentials, query text, or cached payloads. Redis does not participate in readiness because cache loss must not take the catalogue capability offline.

Cache-aside permits a bounded stale-read window during concurrent read/repopulate and mutation races. TTLs bound that window, and broad post-commit invalidation reduces it. Inventory mutation and future reservation decisions must always use PostgreSQL rather than cached availability. Production can add versioned keys, event-driven invalidation, and observed staleness metrics where measurements justify the complexity.

Production should use managed Redis with private connectivity, TLS, authentication/ACL integration, cross-zone replication, automatic failover, maintenance controls, monitored memory/eviction pressure, and tested application fallback. Replication improves cache availability but does not make Redis authoritative.

## Transactional outbox and Kafka production

Product creation/update, effective-price changes, stock initialization/adjustment, and low/out-of-stock transitions append a versioned event envelope to `domain_event_outbox` in the same PostgreSQL transaction as the authoritative change. A background relay leases committed rows, publishes to the fixed Kafka bootstrap servers, and marks each row only after acknowledgement. Kafka failure defers publication; it does not roll back or corrupt the already committed catalogue state and does not make readiness fail.

Delivery is at least once. A crash after Kafka acknowledgement but before the outbox acknowledgement can produce the same `event_id` again. Consumers must deduplicate by `event_id`. Events are keyed by aggregate ID; the PoC topics each have one partition, while production ordering is guaranteed only within an aggregate key/partition and never across topics. See the [event publication design](../../docs/architecture/catalogue-event-publication.md).

Operational endpoints remain:

- `GET /health/live`
- `GET /health/ready` — returns `503` when PostgreSQL is unavailable
- `GET /api/v1/info`

Interactive OpenAPI is available at `/docs`; the machine-readable contract is `/openapi.json`.

## Configuration

Copy values from `.env.example` into an environment-specific secret/configuration mechanism. `DATABASE_URL`, `REDIS_PASSWORD`, and bearer tokens must never be committed or logged. Kafka bootstrap servers and relay tuning contain no credentials. Kubernetes uses separate database and cache Secrets in `shopsphere-apps`; Redis receives its matching password through a Secret in `shopsphere-data`.

JWT validation verifies RS256 signature, issuer, audience, expiry, subject, and allow-listed realm/client roles. The service remains authoritative for authorization when requests arrive through the API Gateway.

## Local development and validation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/ruff format --check app tests migrations
.venv/bin/ruff check app tests migrations
.venv/bin/black --check app tests migrations
.venv/bin/bandit -q -r app
.venv/bin/pytest
DATABASE_URL=postgresql+psycopg://catalogue_app:REPLACE_AT_RUNTIME@localhost:5432/catalogue_db \
  .venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

Tests use signed simulated identities and an in-memory repository adapter for deterministic API/domain behavior. SQLAlchemy metadata and monetary types have focused tests. Alembic must additionally be validated against PostgreSQL before deployment; SQLite is not treated as migration evidence.

## Current limitations

- Fixed Catalogue and Inventory routes are registered in API Gateway source, covered by isolated gateway tests, and the internal Gateway workload is Ready. A live unauthenticated route reached catalogue-service and returned its authoritative `401`; an authenticated catalogue journey has not passed.
- The React catalogue/inventory feature and API Gateway-only client are implemented; six focused frontend tests and the production build passed. The frontend is not deployed in Kubernetes and this is not end-to-end evidence.
- The PoC uses one `PRIMARY` inventory location; multi-warehouse workflows are not exposed yet.
- Order reservations, releases, fulfilment, and cross-service order integration are not implemented.
- Price scheduling, markets, tax, promotions, and multiple price books are outside the PoC pricing model.
- Search uses PostgreSQL rather than Elasticsearch/OpenSearch.
- No catalogue/inventory Kafka consumer, schema registry, outbox archival job, or event-driven dashboard is implemented.
- Redis is one ephemeral pod on the same VM and is neither replicated nor highly available. Cache loss is tolerated by PostgreSQL fallback.
- Kafka is one combined broker/controller and retained PVC on the same VM. It is not highly available and its private PoC listener has no TLS, authentication, or ACLs.

## Current validation evidence

- 48 catalogue-service tests passed with 80% aggregate statement coverage.
- Ruff and Bandit completed with zero findings; 46 catalogue Python files passed Black checks.
- The three-revision Alembic chain has one base and one head (`003_domain_event_outbox`), and the PostgreSQL offline upgrade SQL compiled.
- Catalogue-service, Redis, Kafka and API Gateway manifests passed non-destructive validation; current read-only checks observed one Ready instance of each.
- Earlier controlled platform evidence records simulated category/product/price/inventory changes and successful outbox/Kafka publication.
- The explicitly enabled live catalogue integration report contains 11 passed tests in 79.09 seconds with zero failures, errors or skips; it includes authenticated Gateway, RBAC, statistics, cache, event publication, Redis fallback and Kafka recovery scenarios.

PostgreSQL is the source of truth. Redis is a disposable performance optimization only.
Kafka is asynchronous domain-event transport; it does not determine whether a command
committed. The transactional outbox provides at-least-once delivery, so consumers must
deduplicate by `event_id`.

The PoC runs one PostgreSQL instance, one Redis instance, one Kafka broker/controller,
one Kubernetes node and one physical VM. It has no host-level high availability.
Production should use managed/HA PostgreSQL with backups and PITR, replicated Redis,
multi-broker or managed Kafka, multiple Kubernetes nodes and zones, measured autoscaling,
and stronger private network, workload identity, secret-management and policy boundaries.
