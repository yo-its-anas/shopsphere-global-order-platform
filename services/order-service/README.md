# Order Service

FastAPI service for the ShopSphere Enterprise Order Processing boundary. The implemented
scope includes authenticated customer-owned carts and idempotent checkout orchestration.
It also includes actor-scoped order history and controlled lifecycle transitions.
Payment, shipment tracking, Gateway routes, frontend screens, and Kubernetes deployment
remain outside this implementation.

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

- Checkout re-fetches authoritative active product, price, currency, and availability
  through catalogue-service; the request accepts no commercial values.
- Decimal `NUMERIC(19,4)` immutable line snapshots preserve SKU, name, quantity, unit
  price, line total, and reservation reference.
- Customer-scoped `Idempotency-Key` records prevent duplicate orders and recover a
  committed confirmation after retries.
- A sequential reservation Saga compensates earlier lines when a later reservation or
  local order write fails. Failed release evidence remains in `checkout_attempts` for
  reconciliation.
- A successful checkout atomically records the order, status history, safe audit events,
  cart completion, and `order.created.v1`/`order.confirmed.v1` outbox intents.
- The outbox relay is at-least-once: Kafka failure does not roll back a committed order;
  consumers must be idempotent by `event_id`.
- Customers can list and retrieve only their own immutable order snapshots, history and
  safe audit activity; cross-customer identifiers return `404`.
- Support has operational read access only. `operations_admin` alone can perform the
  explicit `CONFIRMED → PROCESSING → FULFILLED` progression.
- Customer/admin cancellation is limited to `CONFIRMED` or `PROCESSING`, releases active
  reservations, is idempotent, and creates history, audit and versioned events. It does
  not represent a refund.

Browser values and cart display snapshots never determine an order total or inventory
decision.

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
| `POST` | `/api/v1/orders/checkout` | `customer` | Checkout the caller's active cart; requires `Idempotency-Key`. |
| `GET` | `/api/v1/orders/me` | `customer` | Paginated own-order list with status/sort controls. |
| `GET` | `/api/v1/orders/me/{order_id}` | `customer` | Own immutable order detail. |
| `GET` | `/api/v1/orders/me/{order_id}/history` | `customer` | Own status history. |
| `GET` | `/api/v1/orders/me/{order_id}/audit` | `customer` | Own safe paginated transaction audit. |
| `POST` | `/api/v1/orders/me/{order_id}/cancellation` | `customer` | Idempotently cancel an eligible own order. |
| `GET` | `/api/v1/orders/admin...` | `support`, `operations_admin` | Governed operational order/history/audit reads. |
| `POST` | `/api/v1/orders/admin/{order_id}/status` | `operations_admin` | Explicit processing/fulfilment transition. |
| `POST` | `/api/v1/orders/admin/{order_id}/cancellation` | `operations_admin` | Cancel an eligible order. |

Non-owned item identifiers return `404`, limiting both IDOR access and resource
enumeration. Only the `customer` role has cart mutation rights; support and
`operations_admin` do not receive customer impersonation implicitly.

## Configuration

Copy `.env.example` and supply values through the runtime environment. Required runtime
dependencies are configured by `DATABASE_URL`, `KEYCLOAK_ISSUER`,
`CATALOGUE_SERVICE_URL`, and a confidential `SERVICE_TOKEN_*` identity authorized only
for internal inventory reservation commands. Optional `KAFKA_BOOTSTRAP_SERVERS` enables
the recoverable outbox relay. Credentials belong in a secret manager or Kubernetes
Secret and must not be committed. The Catalogue and token URLs are trusted fixed origins;
clients cannot supply an upstream URL.

## Database migration

Migration `001_shopping_cart` creates `shopping_carts` and `cart_items`. Migration
`002_order_checkout` adds orders, immutable commercial items, status history, transaction
audit, durable checkout attempts/reconciliation evidence, and the event outbox. Migration
`003_order_lifecycle` expands the database status constraint to the documented finite
state set. Together they enforce UUID
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

The API tests use signed synthetic JWTs, simulated products/reservations, and an in-memory
repository adapter. They validate success, authoritative recalculation, precision,
multi-line behavior, inventory failures and compensation, idempotent retry/conflict,
ownership, audit/history, and outbox intent. PostgreSQL schema structure is validated
independently through Alembic. No real credentials, customer records, or tokens are used.

The target order model and reservation Saga are documented in
[`docs/architecture/order-processing-domain-design.md`](../../docs/architecture/order-processing-domain-design.md)
and [`ADR-011`](../../docs/adr/ADR-011-reservation-based-order-saga.md). Live PoC service
identity, migration, reservation, Kafka publication, Gateway, and UI validation remain
pending until the order-service is deployed.
