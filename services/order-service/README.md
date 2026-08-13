# Order Service

FastAPI service for the ShopSphere Enterprise Order Processing boundary. The current
implemented scope is an authenticated, customer-owned shopping cart. Checkout, inventory
reservation, orders, payment, order lifecycle, order events, Gateway routes, frontend
screens, and Kubernetes deployment remain planned.

## Implemented behavior

- One controlled active cart per Keycloak subject and currency, enforced by PostgreSQL.
- Automatic idempotent cart creation on `GET /api/v1/carts/me`.
- Add, update, remove, and clear cart items.
- Duplicate product additions increase the existing line instead of creating duplicate
  records.
- Product existence and active/searchable state are checked through a fixed,
  environment-configured catalogue-service client.
- Catalogue price and availability values are retained only as display snapshots.
- Display subtotals use `Decimal`/`NUMERIC(19,4)` and are explicitly non-authoritative.
- Keycloak RS256 signature, issuer, audience, expiry, subject, and role validation.
- Subject-derived ownership: no request field can select a customer identity.
- Structured request/mutation logs and correlation IDs without bearer-token logging.
- Database-aware readiness; catalogue failure returns a safe dependency response when a
  product is added, but does not affect database readiness.

Final checkout must fetch authoritative price and availability again. Browser values and
cart snapshots must never determine an order total or inventory decision.

## API

| Method | Path | Role | Behavior |
| --- | --- | --- | --- |
| `GET` | `/health/live` | Public/internal probe | Process liveness. |
| `GET` | `/health/ready` | Public/internal probe | PostgreSQL readiness. |
| `GET` | `/api/v1/info` | Public | Non-sensitive service metadata. |
| `GET` | `/api/v1/carts/me` | `customer` | Create if absent and return the caller's active cart. |
| `POST` | `/api/v1/carts/me/items` | `customer` | Validate a product through Catalogue and add/increment it. |
| `PATCH` | `/api/v1/carts/me/items/{item_id}` | `customer` | Replace an owned line quantity. |
| `DELETE` | `/api/v1/carts/me/items/{item_id}` | `customer` | Remove an owned line. |
| `DELETE` | `/api/v1/carts/me/items` | `customer` | Clear the caller's cart. |

Non-owned item identifiers return `404`, limiting both IDOR access and resource
enumeration. Only the `customer` role has cart mutation rights; support and
`operations_admin` do not receive customer impersonation implicitly.

## Configuration

Copy `.env.example` and supply values through the runtime environment. Required runtime
dependencies are configured by `DATABASE_URL`, `KEYCLOAK_ISSUER`, and
`CATALOGUE_SERVICE_URL`. Credentials belong in a secret manager or Kubernetes Secret and
must not be committed. The Catalogue URL is a trusted fixed origin; clients cannot supply
an upstream URL.

## Database migration

Migration `001_shopping_cart` creates `shopping_carts` and `cart_items`. It enforces UUID
keys, one active cart per subject/currency, one line per product/cart, positive bounded
quantities, positive Decimal snapshot prices, foreign-key cleanup, UTC-capable timestamps,
and an optimistic cart version. It does not query or reference catalogue database tables.

```bash
DATABASE_URL='postgresql+psycopg://<user>:<password>@<host>:5432/order_db' \
  .venv/bin/alembic upgrade head
```

Never put a real database URL in source control or terminal screenshots.

## Local validation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m black --check app tests migrations
.venv/bin/python -m ruff check app tests migrations
.venv/bin/python -m bandit -r app
.venv/bin/python -m pytest
.venv/bin/alembic heads
docker build -t shopsphere/order-service:local .
```

The API tests use signed synthetic JWTs, simulated products, and an in-memory repository
adapter. PostgreSQL schema structure is validated independently through Alembic. No real
credentials, customer records, or tokens are used.

The target order model and reservation Saga are documented in
[`docs/architecture/order-processing-domain-design.md`](../../docs/architecture/order-processing-domain-design.md)
and
[`ADR-011`](../../docs/adr/ADR-011-reservation-based-order-saga.md). Those future designs
must not be interpreted as implemented checkout behavior.
