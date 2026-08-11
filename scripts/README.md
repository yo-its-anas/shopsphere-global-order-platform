# Scripts

Contains small, reviewed automation entry points for repeatable local and CI tasks. Scripts must be safe by default, portable where practical, and must not embed credentials.

## Environment validation

- `check-host.sh` reports read-only Ubuntu host capacity and network-listener information.
- `check-docker.sh` checks the Docker CLI, daemon access, Compose, and Buildx.
- `check-kubernetes-tools.sh` checks local `kubectl` and kind clients without contacting or changing a cluster.
- `check-terraform.sh` checks the Terraform CLI.
- `check-jenkins.sh` reports only non-sensitive systemd service state.
- `capture-tool-versions.sh` writes sanitized version evidence to `docs/evidence/tool-versions.md`.

Run all checks with `make doctor`. A non-zero result means one or more prerequisites need attention; scripts never install packages or modify host services.

## PostgreSQL operations

- `validate-postgresql-manifests.sh` renders and checks the PoC PostgreSQL manifests without changing the cluster.
- `check-postgresql.sh` performs read-only checks for workload readiness, ClusterIP-only networking, bound persistence, and the required logical database names.
- `create-postgresql-secret.sh` is an explicit operational helper. It creates the Kubernetes Secret directly from hidden prompts, or generates strong values only when `--generate` is supplied. It never prints credentials and preserves an existing Secret.

## Keycloak operations

- `validate-keycloak-manifests.sh` validates the Kubernetes resources and sanitized realm JSON without changing the cluster.
- `configure-keycloak.sh` idempotently reconciles the ShopSphere client policies, dedicated `view-events` activity reader, and namespace-scoped runtime Secret after realm import without displaying credentials.
- `check-keycloak.sh` performs non-destructive checks for readiness, internal service exposure, PostgreSQL connectivity, realm settings, roles, clients, PKCE enforcement, and authentication-event recording. It requests a least-privilege service token so Keycloak produces a verifiable client authentication event; no token is displayed.
- `create-keycloak-secret.sh` copies the existing Keycloak database credential into a namespace-scoped Secret and creates bootstrap administrator credentials from hidden prompts, or generates them only when `--generate` is supplied. It never prints credential values and preserves an existing Secret.
- `create-customer-service-secret.sh` derives a percent-encoded customer database URL from the existing PostgreSQL credential and creates a namespace-scoped Secret directly through the Kubernetes API. It never prints the URL or credential and preserves an existing Secret.
- `validate-customer-service-manifests.sh` renders and statically checks the internal customer-service Kustomize overlay without changing the cluster.
- `check-customer-service.sh` verifies the deployed workload, ClusterIP-only Service, and health endpoints without reading credentials.
- `create-redis-secret.sh` creates matching namespace-scoped Redis runtime Secrets from hidden input or explicit generated mode without displaying values.
- `validate-redis-manifests.sh` checks authenticated, ephemeral, ClusterIP-only Redis manifests and hardened workload settings.
- `check-redis.sh` verifies Redis readiness, authenticated ping, and ClusterIP-only exposure without reading credentials.
- `validate-catalogue-service-manifests.sh` checks the internal cache-enabled catalogue-service workload and dependency references.
- `check-catalogue-service.sh` verifies catalogue-service health, ClusterIP-only exposure, and authenticated Redis connectivity without displaying credentials.
