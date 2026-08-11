# Catalogue Service

FastAPI service for Product Catalogue categories, product lifecycle, PostgreSQL search, and effective pricing. Inventory stock, reservations, movements, Redis, Kafka, API Gateway routing, and Kubernetes application deployment are not implemented here.

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

Customers see only active, searchable products in active categories and current active prices. Support can read inactive operational records and pricing history but cannot modify catalogue state. `operations_admin` owns all mutations. SKU is immutable after registration and unique after trim/uppercase normalization. Category slug is unique after trim/lowercase normalization.

`GET /api/v1/products` supports `query`, `sku`, `category_id`, `status`, `offset`, `limit`, `sort_by`, and `sort_direction`. PostgreSQL `ILIKE` search covers product name, SKU, and description. Customers cannot use status filters to reveal inactive records.

Prices use Python `Decimal` and PostgreSQL `NUMERIC(19,4)`. A price update is immediately effective: it closes the previous active record for the product/currency and appends a new active record. `include_history=true` is restricted to support and operations roles. The supported ISO currency subset is controlled by `SUPPORTED_CURRENCIES`.

Operational endpoints remain:

- `GET /health/live`
- `GET /health/ready` — returns `503` when PostgreSQL is unavailable
- `GET /api/v1/info`

Interactive OpenAPI is available at `/docs`; the machine-readable contract is `/openapi.json`.

## Configuration

Copy values from `.env.example` into an environment-specific secret/configuration mechanism. `DATABASE_URL` and bearer tokens must never be committed or logged. The Kubernetes platform already provides the `shopsphere-catalogue-service-database` runtime Secret, but no catalogue-service Deployment consumes it yet.

JWT validation verifies RS256 signature, issuer, audience, expiry, subject, and allow-listed realm/client roles. The service remains authoritative for authorization even when a future API Gateway route is added.

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

- Catalogue routes are not yet registered in API Gateway.
- The catalogue-service is not yet deployed to Kubernetes.
- Inventory stock and availability behavior is deliberately absent.
- Price scheduling, markets, tax, promotions, and multiple price books are outside the PoC pricing model.
- Search uses PostgreSQL rather than Elasticsearch/OpenSearch.
- Domain-event publication remains Planned; no Kafka claim is made.
