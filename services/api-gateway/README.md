# API Gateway

FastAPI transport and policy boundary for ShopSphere APIs. It forwards the implemented customer and Catalogue/Inventory capabilities to fixed internal services and contains no customer, catalogue, inventory, order, or analytics domain logic.

## Customer route mapping

| External gateway path | Internal customer-service path |
| --- | --- |
| `/api/v1/customers/me` | `/api/v1/customers/me` |
| `/api/v1/customers/me/addresses[/{address_id}[/default]]` | Corresponding `/api/v1/customers/me/addresses...` path |
| `/api/v1/customers/me/activity` | `/api/v1/customers/me/activity` |
| `/api/v1/customers/me/audit-history` | `/api/v1/customers/me/audit-history` |
| `/api/v1/admin/customers` | `/api/v1/admin/customers` |
| `/api/v1/admin/customers/{customer_id}` | `/api/v1/admin/customers/{customer_id}` |
| `/api/v1/admin/customers/{customer_id}/{activity\|audit-history\|status}` | Corresponding `/api/v1/admin/customers/{customer_id}/...` path |

Only the exact HTTP method and path combinations implemented by customer-service are registered. Unknown customer subpaths and other capability prefixes are not forwarded.

## Catalogue and Inventory route mapping

External and internal paths currently match beneath `/api/v1`; they use separate configured origins.

| External gateway path | Methods | Internal catalogue-service path |
| --- | --- | --- |
| `/api/v1/categories` | `GET`, `POST` | `/api/v1/categories` |
| `/api/v1/categories/{category_id}` | `GET`, `PATCH` | `/api/v1/categories/{category_id}` |
| `/api/v1/products` | `GET`, `POST` | `/api/v1/products` |
| `/api/v1/products/{product_id}` | `GET`, `PATCH` | `/api/v1/products/{product_id}` |
| `/api/v1/products/{product_id}/deactivate` | `POST` | Same path |
| `/api/v1/products/{product_id}/prices` | `GET` | Same path |
| `/api/v1/products/{product_id}/prices/{currency_code}` | `PUT` | Same path |
| `/api/v1/inventory` | `GET` | `/api/v1/inventory` |
| `/api/v1/inventory/statistics` | `GET` | Same path |
| `/api/v1/inventory/products/{product_id}` | `GET` | Same path |
| `/api/v1/inventory/products/{product_id}/availability` | `GET` | Same path |
| `/api/v1/inventory/products/{product_id}/initialize` | `POST` | Same path |
| `/api/v1/inventory/products/{product_id}/adjustments` | `POST` | Same path |
| `/api/v1/inventory/products/{product_id}/settings` | `PATCH` | Same path |
| `/api/v1/inventory/products/{product_id}/movements` | `GET` | Same path |

UUID and currency path parameters are structurally validated before forwarding. Search, filter, sorting, repeated query parameters, and pagination values are forwarded unchanged for catalogue-service validation. No catch-all route exists, so request headers or paths cannot select an arbitrary upstream.

The gateway propagates `Authorization`, `Accept`, `Content-Type`, query parameters, request bodies, and the validated `X-Request-ID`. It never logs or returns bearer-token values. Customer-service and catalogue-service remain authoritative for JWT signature, issuer, audience, role, ownership, visibility, and mutation authorization; gateway JWT/RBAC enforcement is not claimed as implemented.

The upstream origins are fixed when the application starts from `CUSTOMER_SERVICE_URL` and `CATALOGUE_SERVICE_URL`. Validation permits only HTTP(S) origins without credentials, query, fragment, or path. Each capability has a bounded independent timeout, and redirect following is disabled.

Timeouts return a standardized `504`; connection failures return `503`; other transport failures return `502`. Responses omit internal server headers and failure details. Structured gateway logs contain correlation, route outcome, service identifier, status, and duration, but no authorization headers.

`/health/live` remains dependency-free. `/health/ready` checks both customer-service and catalogue-service readiness and returns a non-sensitive `503 not_ready` response when either required synchronous dependency is unavailable or not ready. It does not expose which private address failed.

## Configuration

- `CUSTOMER_SERVICE_URL` — internal customer-service origin, normally the Kubernetes service DNS name;
- `CUSTOMER_SERVICE_TIMEOUT_SECONDS` — bounded request timeout from greater than zero through 30 seconds;
- `CATALOGUE_SERVICE_URL` — fixed internal catalogue-service origin;
- `CATALOGUE_SERVICE_TIMEOUT_SECONDS` — bounded catalogue request timeout from greater than zero through 30 seconds;
- `APP_ENV`, `LOG_LEVEL`, `SERVICE_NAME`, and `SERVICE_VERSION` — non-secret runtime metadata.

## Local development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/ruff check app tests
.venv/bin/black --check app tests
.venv/bin/bandit -q -r app
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
```

The generated OpenAPI document describes the fixed customer and catalogue/inventory transport routes and normalized `502`, `503`, and `504` responses. A hardened, ClusterIP-only Kubernetes PoC workload is defined under `platform/kubernetes`; public ingress is not configured. Order and analytics routing, gateway-side JWT defence in depth, rate limits, workload-to-workload identity, and circuit breaking remain planned.
