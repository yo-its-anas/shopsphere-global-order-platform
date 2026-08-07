# API Gateway

Day 1 FastAPI gateway placeholder. It does not proxy requests, authenticate users, authorize roles, connect to Keycloak, or implement any customer, catalogue, order, or analytics domain behavior.

## Local development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
```

The current API exposes only `/health/live`, `/health/ready`, `/api/v1/info`, and generated OpenAPI documentation. Configuration uses `APP_ENV`, `LOG_LEVEL`, `SERVICE_NAME`, and `SERVICE_VERSION`; none is a secret.

Future gateway work may add governed routing and identity enforcement. Domain business logic must remain in its owning service.
