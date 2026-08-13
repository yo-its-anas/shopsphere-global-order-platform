# Foundation CI Validation Pipeline

The root `Jenkinsfile` defines the foundation validation pipeline for the ShopSphere monorepo. It establishes initial quality controls; the broader DevSecOps and deployment implementation remains planned.

## Pipeline behavior

The declarative pipeline uses one Jenkins workspace and executes these stages sequentially with fail-fast shell behavior:

1. Explicit source checkout.
2. Non-sensitive host and tool diagnostics.
3. Required monorepo path and Git whitespace validation.
4. Customer-service dependency installation in an isolated Python virtual environment, followed by `pip check`.
5. Black formatting checks and Ruff linting for all five Python services.
6. An enforcing Bandit scan of customer-service with a JSON evidence report.
7. Pytest unit tests for all five services with individual JUnit XML reports.
8. Locked frontend installation using `npm ci`.
9. Frontend Prettier and ESLint checks.
10. Vitest execution with JUnit XML output and a production frontend build.
11. A dedicated customer-service Docker build followed by validation builds for the remaining deployable images.
12. Terraform formatting validation.
13. Terraform provider initialization with `-backend=false` and configuration validation.
14. Offline kind-shape, PoC Kustomize, and customer-service manifest validation.
15. JUnit publication and archival of XML and security evidence under `test-results/`.

The pipeline has a 60-minute overall timeout plus tighter stage timeouts, timestamps, disabled concurrent runs, and retention of 20 builds for at most 30 days. A failure stops subsequent stages. If failure occurs after any test report is created, the pipeline-level `post` handler attempts to publish and archive that partial evidence.

## Agent prerequisites

The Jenkins agent must provide:

- Bash, Git, Python 3 with `venv`, Node.js 20.19 or later, and npm;
- Docker CLI, Compose plugin, Buildx, and permission for the Jenkins identity to use the Docker daemon;
- kubectl and kind;
- Terraform compatible with `infrastructure/terraform/versions.tf`;
- outbound access to the approved Python, npm, Terraform-provider, and container registries.

The agent must not solve missing access with `sudo`, a privileged container, a world-writable Docker socket, or embedded credentials. Registry and cloud identities require reviewed Jenkins credential bindings before those integrations are enabled; none are configured here.

Docker validation creates locally tagged `ci-<build number>` images. Host-level image retention and garbage collection are an administrator responsibility and are intentionally not implemented as destructive pipeline cleanup.

## Explicit non-goals

- No application, infrastructure, kind, Kubernetes, or cloud deployment.
- No Terraform plan or apply.
- No cluster creation or deletion.
- No image publication.
- No authentication or secret retrieval.
- No claim that DevSecOps controls are complete.

## Planned DevSecOps expansion

Bandit is an active, fail-closed customer-service gate. Findings that make Bandit return a non-zero status fail the build; its JSON report is archived even when that happens. The following gates remain documented in the Jenkinsfile but intentionally have no executable stages yet:

- Semgrep;
- Trivy filesystem and image scanning;
- Python and npm dependency scanning;
- OPA policy checks;
- artifact provenance and registry publication;
- approval-controlled PoC deployment, smoke testing, and rollback validation.

The expanded implementation must define severity thresholds, false-positive governance, credential bindings, evidence retention, approval boundaries, and failure behavior before any gate or deployment becomes active.

## Local command alignment

The pipeline uses the same repository-level building blocks available to developers:

```bash
make validate-kubernetes
make validate-customer-service
terraform -chdir=infrastructure/terraform fmt -check -recursive
terraform -chdir=infrastructure/terraform init -backend=false -input=false
terraform -chdir=infrastructure/terraform validate
```

Python commands execute inside an ephemeral workspace virtual environment. Frontend commands execute inside `frontend/` against the committed `package-lock.json`.

## Validation cadence and capability integration policy

All checkout, static analysis, unit test, frontend build, Docker build, Terraform, and Kubernetes validation stages run on every commit. They require no live ShopSphere workload.

The `PoC customer integration tests` stage is the deliberate exception because it exercises live PoC services. Jenkins marks the stage as skipped unless `SHOPSPHERE_RUN_CUSTOMER_INTEGRATION=true`; this is pipeline policy, not a synthetic passing result. When enabled, the job must inject the complete environment contract described in `tests/integration/README.md`, including masked credentials for dedicated test-only Keycloak clients. Missing configuration or unavailable services fail the enabled stage rather than being ignored.

The stage creates randomized simulated identities, exercises only Keycloak, API Gateway, customer-service, and the customer database boundary, then publishes `test-results/integration/customer-identity.xml`. It does not deploy workloads, modify PostgreSQL availability, use bootstrap administrator credentials, or test incomplete business modules.

The separate `PoC catalogue and inventory integration tests` stage runs only when
`SHOPSPHERE_RUN_CATALOGUE_INTEGRATION=true`. It uses randomized synthetic catalogue
records and publishes `test-results/integration/catalogue-inventory.xml`. Normal API
coverage is non-disruptive. Kubernetes observation is separately enabled, and Redis or
Kafka outage/recovery tests require their own explicit opt-ins; a skipped outage test is
reported as skipped and is never converted into a pass. The required environment and
cleanup boundary are documented in `tests/integration/README.md`.

Catalogue validation also installs the catalogue service's pinned dependency set and
runs Black, Ruff, Bandit, Pytest, a dedicated Docker build, focused frontend catalogue
tests, the full frontend production build, Redis/Kafka/catalogue Kubernetes manifest
validation, and an offline Alembic revision-graph/SQL compilation check. Machine-readable
Ruff, Bandit, migration, frontend, backend, and integration evidence is archived.

The pipeline writes capability status files under `test-results/status`. An enabled
suite is pessimistically marked failed before execution and is reclassified from its
JUnit XML afterward. A report containing only skipped tests becomes
`skipped/not applicable`, not passed; partially skipped reports retain exact passed,
failed, and skipped counts. Disabled live suites are explicitly classified
`skipped/not applicable` with a reason.

Jenkins credentials must be bound as masked environment variables by job configuration. The pipeline never echoes configuration values, credentials, access tokens, or refresh tokens.
