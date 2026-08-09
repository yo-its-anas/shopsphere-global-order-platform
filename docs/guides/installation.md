# Customer Capability Installation Guide

This guide prepares the existing Ubuntu 22.04 PoC host for ShopSphere Customer Identity and Account Management. It does not install host packages automatically and does not apply Terraform.

## Prerequisites

- Docker with current-user daemon access, Compose, and Buildx;
- kubectl and kind;
- Python 3.10 or later with `venv`;
- Node.js 20.19 or later and npm;
- Bash, Make, Git, and sufficient disk/memory for the single-node cluster; and
- access to approved package and container registries.

Run the non-destructive checks:

```bash
make doctor
make validate-shell
make validate-kubernetes
make validate-postgresql
make validate-keycloak
make validate-customer-service
```

Missing tools are reported and are never installed by these commands. Do not use Terraform apply: the VM already exists, and the Terraform module is import-first with deletion safeguards.

## Application dependencies

Install Python and frontend dependencies into local, ignored directories:

```bash
python3 -m venv services/customer-service/.venv
services/customer-service/.venv/bin/python -m pip install -e 'services/customer-service[dev]'

cd frontend
npm ci --no-audit --no-fund
```

Package installation requires approved network access. Do not run it with `sudo`, and do not commit `.venv`, `node_modules`, populated environment files, test credentials, or generated secrets.

## Configuration boundaries

Use only the committed `.env.example` and Kubernetes `*.example.yaml` files as templates. The frontend may receive public OIDC configuration through `VITE_*`; it must never receive client secrets. PostgreSQL passwords, Keycloak bootstrap credentials, customer-service database URLs, and the activity-reader secret must be injected through the supplied secret helpers or an approved external secret manager.

The PoC URL examples use local HTTP and protected port forwarding. They are not production security settings. Production requires TLS, private administration, external secret management, and independent identity/database infrastructure.

## Validation status

The current host has a Ready single-node kind cluster with Ready PostgreSQL, Keycloak, and customer-service workloads. This is evidence for the current environment, not a clean-host installation rehearsal. API Gateway and frontend are not currently deployed in Kubernetes, so a complete browser journey requires separately running those components and executing the opt-in integration tests.
