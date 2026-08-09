# API Gateway

FastAPI transport and policy boundary for ShopSphere APIs. It forwards the implemented customer capability to customer-service and contains no customer, catalogue, order, or analytics domain logic.

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

The gateway propagates `Authorization`, `Accept`, `Content-Type`, query parameters, request bodies, and the validated `X-Request-ID`. It never logs or returns bearer-token values. Customer-service remains the authoritative JWT signature, issuer, audience, role, and resource-ownership enforcement point; gateway JWT validation is not claimed as implemented.

The customer-service origin is fixed when the application starts from `CUSTOMER_SERVICE_URL`. Validation permits only an HTTP(S) origin without credentials, query, fragment, or path, so request data cannot select an upstream host. Redirect following is disabled.

Timeouts return a standardized `504`; connection failures return `503`; other transport failures return `502`. Responses omit internal server headers and failure details. Structured gateway logs contain correlation, route outcome, service identifier, status, and duration, but no authorization headers.

`/health/live` remains dependency-free. `/health/ready` checks customer-service readiness and returns a non-sensitive `503 not_ready` response when the dependency is unavailable or not ready.

## Configuration

- `CUSTOMER_SERVICE_URL` — internal customer-service origin, normally the Kubernetes service DNS name;
- `CUSTOMER_SERVICE_TIMEOUT_SECONDS` — bounded request timeout from greater than zero through 30 seconds;
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

The generated OpenAPI document describes the fixed customer transport routes and gateway failure responses. Catalogue, order, and analytics routing; gateway-side JWT enforcement; rate limits; workload-to-workload identity; circuit breaking; and deployment of the gateway/customer-service path remain planned.
