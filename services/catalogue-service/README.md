# Catalogue Service

FastAPI foundation for the planned product catalogue, pricing, availability, and inventory boundary. No catalogue business behavior, persistence, Redis caching, or authentication is implemented.

The proposed bounded contexts, entities, invariants, authorization rules, concurrency strategy, events, and production evolution are defined in the [Product Catalogue and Inventory domain design](../../docs/architecture/catalogue-inventory-domain-design.md). That design is not implementation evidence.

## Local development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
```

The current API exposes only `/health/live`, `/health/ready`, `/api/v1/info`, and generated OpenAPI documentation. Configuration uses `APP_ENV`, `LOG_LEVEL`, `SERVICE_NAME`, and `SERVICE_VERSION`; none is a secret.
