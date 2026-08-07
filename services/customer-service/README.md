# Customer Service

Day 1 FastAPI skeleton for the planned customer profile, contact, address, and account boundary. No customer business behavior, persistence, identity integration, or authentication is implemented.

## Local development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
```

The current API exposes only `/health/live`, `/health/ready`, `/api/v1/info`, and generated OpenAPI documentation. Configuration uses `APP_ENV`, `LOG_LEVEL`, `SERVICE_NAME`, and `SERVICE_VERSION`; none is a secret.
