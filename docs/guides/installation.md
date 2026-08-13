# ShopSphere PoC Installation Guide

This guide prepares the existing Ubuntu 22.04 PoC host for implemented Customer Identity,
Product Catalogue/Inventory and Enterprise Order Processing capabilities. It does not install host packages
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
make validate-order-service
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

python3 -m venv services/order-service/.venv
services/order-service/.venv/bin/python -m pip install -e 'services/order-service[dev]'

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

PostgreSQL is the source of truth for customer, catalogue, inventory and order state.
Redis is an optional performance cache. Kafka carries asynchronous events after
PostgreSQL commit. No password, token or service credential belongs in domain data.

## Evidence boundary

Current evidence records 60 passing catalogue tests, 46 passing order-service tests,
focused catalogue and order frontend tests, successful frontend production builds,
validated Catalogue and Order Alembic chains, and passing platform manifests. The
catalogue integration suite passed all 11 scenarios. The explicitly enabled Order E2E
suite passed prerequisites and scenarios A–I through API Gateway. These are retained
test results; they do not replace a clean-host installation rehearsal or a browser-driven
order demonstration, which remain **Pending / Not Verified**.
