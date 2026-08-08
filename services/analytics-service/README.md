# Analytics Service

FastAPI foundation for the planned reporting views and executive operational insights boundary. No analytics business behavior, Kafka consumption, persistence, dashboard implementation, or authentication is implemented.

## Local development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
```

The current API exposes only `/health/live`, `/health/ready`, `/api/v1/info`, and generated OpenAPI documentation. Configuration uses `APP_ENV`, `LOG_LEVEL`, `SERVICE_NAME`, and `SERVICE_VERSION`; none is a secret.
