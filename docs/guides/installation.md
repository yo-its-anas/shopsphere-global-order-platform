# ShopSphere PoC Installation Guide

This guide prepares the existing Ubuntu 22.04 PoC host for implemented Customer Identity
and Product Catalogue/Inventory capabilities. It does not install host packages
automatically, apply Terraform, or deploy production infrastructure.

## Prerequisites and validation

- Docker with current-user daemon access, Compose and Buildx;
- kubectl and kind;
- Python 3.10 or later with `venv`;
- Node.js 20.19 or later and npm;
- Bash, Make and Git; and
- approved package/container registry access.

```bash
make doctor
make validate-shell
make validate-kubernetes
make validate-postgresql
make validate-keycloak
make validate-redis
make validate-kafka
make validate-customer-service
make validate-catalogue-service
make validate-api-gateway
```

These commands are non-destructive manifest/tool checks. Missing tools are reported and
never installed automatically. The VM already exists; Terraform remains import-first and
must not be applied without reviewed variables, imports and plan evidence.

## Application dependencies

```bash
python3 -m venv services/customer-service/.venv
services/customer-service/.venv/bin/python -m pip install -e 'services/customer-service[dev]'

python3 -m venv services/catalogue-service/.venv
services/catalogue-service/.venv/bin/python -m pip install -e 'services/catalogue-service[dev]'

cd frontend
npm ci --no-audit --no-fund
```

Do not use `sudo` for application dependencies or commit `.venv`, `node_modules`,
populated environment files, generated Kubernetes Secrets, credentials or tokens.

## Configuration boundaries

Use committed `*.example` files as variable-name templates only. The frontend receives
public `VITE_*` OIDC/API configuration and no client secret. PostgreSQL, Redis, Keycloak
and test-client credentials must be injected through provided helpers, protected shell
variables or Jenkins credential bindings.

PostgreSQL is the source of truth for catalogue, pricing, inventory, movements and
outbox state. Redis is an optional performance cache. Kafka carries asynchronous events
after PostgreSQL commit. No password, token or service credential belongs in catalogue
domain data.

## Evidence boundary

Current repository validation records 48 passing catalogue backend tests, 6 passing
focused frontend tests, a successful frontend production build, one valid three-revision
Alembic chain, a successful catalogue Docker build, and passing non-destructive platform
manifests. Ready internal PoC workloads have also been observed. The 11 live catalogue
integration tests were skipped, so a complete authenticated user journey remains
**Pending / Not Verified**.
