# Customer Service

FastAPI foundation for the planned customer business profile, contact, address, account metadata, customer-domain audit history, and customer activity presentation boundary. Keycloak, not this service, owns authentication, credentials, password policy, token issuance, identity roles, login/logout, and authentication events. This service must never store passwords, password hashes, reset tokens, or recovery credentials.

No customer business behavior, persistence, identity integration, authentication, authorization, audit storage, or activity integration is currently implemented. The governing boundary and security flows are documented in [ADR-005](../../docs/adr/ADR-005-keycloak-identity-rbac.md).

## Local development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
```

The current API exposes only `/health/live`, `/health/ready`, `/api/v1/info`, and generated OpenAPI documentation. Configuration uses `APP_ENV`, `LOG_LEVEL`, `SERVICE_NAME`, and `SERVICE_VERSION`; none is a secret.
