# Order Service

FastAPI foundation for the planned order capture, validation, lifecycle, orchestration,
and domain-event boundary. The PoC platform provides an empty logical `order_db` owned
by dedicated `order_app`, but no order schema, migration, repository behavior, business
logic, Kafka integration, or authentication is implemented.

The accepted target domain design is documented in
[`docs/architecture/order-processing-domain-design.md`](../../docs/architecture/order-processing-domain-design.md),
with the reservation Saga decision in
[`ADR-011`](../../docs/adr/ADR-011-reservation-based-order-saga.md). Those documents do
not imply that carts, orders, inventory reservations, gateway routes, or events exist.

## Local development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
```

The current API exposes only `/health/live`, `/health/ready`, `/api/v1/info`, and generated OpenAPI documentation. Configuration uses `APP_ENV`, `LOG_LEVEL`, `SERVICE_NAME`, and `SERVICE_VERSION`; none is a secret.
