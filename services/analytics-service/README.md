# Analytics Service

Read-only FastAPI aggregation boundary for the ShopSphere Executive Business Operations
Dashboard. Customer, Catalogue/Inventory, and Order services remain authoritative; this
service neither owns their transactional data nor queries their databases.

## Implemented API

All business endpoints require a Keycloak-compatible bearer token and return
`generated_at`, `data_status`, and per-source `dependency_status` metadata.

| Endpoint | Data | Roles |
|---|---|---|
| `GET /api/v1/dashboard/summary` | Combined executive KPIs | `operations_admin` |
| `GET /api/v1/dashboard/orders` | Orders, status and simulated revenue | `operations_admin` |
| `GET /api/v1/dashboard/inventory` | Product and inventory aggregates | `support`, `operations_admin` |
| `GET /api/v1/dashboard/customers` | Provisioned customer profile count | `support`, `operations_admin` |
| `GET /api/v1/dashboard/operations` | Domain-service readiness summary | `support`, `operations_admin` |
| `GET /api/v1/dashboard/alerts` | Dependency and persisted inventory conditions | `support`, `operations_admin` |

`GET /health/live`, `GET /health/ready`, `GET /api/v1/info`, OpenAPI, and an internal
`GET /metrics` Prometheus exposition endpoint are preserved. Analytics readiness is
dependency-independent because partial, explicitly labelled dashboard responses are a
supported mode; `/dashboard/operations` reports current dependency readiness.

## Calculation and ownership rules

- `customer_count` counts provisioned customer-service business profiles.
- Product totals and inventory balances come from catalogue-service APIs.
- Order totals and statuses come from order-service administrative APIs.
- Simulated revenue is the sum of server-calculated order totals in `CONFIRMED`,
  `PROCESSING`, and `FULFILLED` states. `CANCELLED`, `FAILED`, and `PENDING` orders do
  not contribute.
- Revenue is preserved per ISO currency. A scalar total is returned only when one
  currency exists; no exchange rate is invented.
- Fulfilment rate is `FULFILLED / (CONFIRMED + PROCESSING + FULFILLED) * 100`.
- Available products are tracked products in either in-stock or low-stock state.

Revenue is labelled simulated because payment settlement is outside the implemented
scope. Aggregates are calculated from persisted PoC records exposed by domain APIs; no
production values are fabricated.

## Resilience and security

Each upstream client is bound to a validated, environment-configured HTTP(S) origin and
uses fixed application paths, bounded pagination, strict response validation, no
redirect following, and a configurable timeout. Callers cannot supply upstream URLs.
The validated bearer token and `X-Request-ID` are forwarded to domain owners, but token
values are excluded from logs and object representations.

If a source fails, its fields are `null`, never a fabricated zero. Other successful
source values remain available and `data_status` becomes `partial`; a single-source
view becomes `unavailable`. Internal transport or response details are not returned.

Prometheus metrics cover bounded HTTP route/status, duration, traffic in progress,
application exception families, aggregation outcomes, dependency outcomes, and static
service information. Customer IDs, order IDs, subjects, email addresses, correlation
IDs, and tokens are not metric labels.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `CUSTOMER_SERVICE_URL` | Fixed customer-service origin | `http://customer-service:8000` |
| `CATALOGUE_SERVICE_URL` | Fixed catalogue-service origin | `http://catalogue-service:8000` |
| `ORDER_SERVICE_URL` | Fixed order-service origin | `http://order-service:8000` |
| `UPSTREAM_TIMEOUT_SECONDS` | Per-request timeout, maximum 30 seconds | `5` |
| `MAXIMUM_AGGREGATE_RECORDS` | Defensive aggregation bound | `10000` |
| `KEYCLOAK_ISSUER` | Expected token issuer; required for live authentication | unset |
| `KEYCLOAK_AUDIENCE` | Required access-token audience | `shopsphere-api` |
| `KEYCLOAK_ROLE_CLIENT_ID` | Client role claim source | `shopsphere-api` |
| `KEYCLOAK_JWKS_URL` | Optional internal JWKS override | issuer-derived |
| `JWT_CLOCK_SKEW_SECONDS` | Bounded validation leeway | `30` |
| `APP_ENV`, `LOG_LEVEL`, `SERVICE_NAME`, `SERVICE_VERSION` | Runtime metadata/logging | safe defaults |

No setting contains a credential. Kubernetes deployment and API Gateway exposure are
separate platform integration work.

## Validate and run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/black --check app tests
.venv/bin/ruff check app tests
.venv/bin/bandit -q -r app
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
docker build -t shopsphere/analytics-service:local .
```

See the
[Executive Operations and Observability Architecture](../../docs/architecture/observability-architecture.md)
and [ADR-012](../../docs/adr/ADR-012-layered-observability-source-owned-kpis.md).
