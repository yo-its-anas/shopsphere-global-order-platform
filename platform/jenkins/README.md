# Foundation CI Validation Pipeline

The root `Jenkinsfile` defines the foundation validation pipeline for the ShopSphere monorepo. It establishes initial quality controls; the broader DevSecOps and deployment implementation remains planned.

## Pipeline behavior

The declarative pipeline uses one Jenkins workspace and executes these stages sequentially with fail-fast shell behavior:

1. Explicit source checkout.
2. Non-sensitive host and tool diagnostics.
3. Required monorepo path and Git whitespace validation.
4. Customer, catalogue, and order service dependency installation in an isolated Python virtual environment, followed by `pip check`.
5. Black formatting checks and Ruff linting for all five Python services.
6. Enforcing Bandit scans of customer-service, catalogue-service, and order-service with JSON evidence reports.
7. Pytest unit tests for all five services with individual JUnit XML reports.
8. Locked frontend installation using `npm ci`.
9. Frontend Prettier and ESLint checks.
10. Full Vitest execution plus focused catalogue/inventory and order-workflow suites with JUnit XML output, followed by a production frontend build.
11. Dedicated customer-service, catalogue-service, and order-service Docker builds followed by validation builds for the remaining deployable images.
12. Terraform formatting validation.
13. Terraform provider initialization with `-backend=false` and configuration validation.
14. Offline kind-shape, PoC Kustomize, customer-service, catalogue-service, order-service, API Gateway, Redis, and Kafka manifest validation.
15. Offline catalogue and order Alembic revision-graph validation and SQL compilation.
16. Optional live order integration and end-to-end validation when deliberately enabled on a PoC-capable agent.
17. JUnit publication and archival of test, lint, security, migration, integration, and end-to-end evidence.

The pipeline has a 90-minute overall timeout plus tighter stage timeouts, timestamps, disabled concurrent runs, and retention of 20 builds for at most 30 days. A failure stops subsequent stages. If failure occurs after any test report is created, the pipeline-level `post` handler attempts to publish and archive that partial evidence.

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

Bandit is an active, fail-closed gate for the customer, catalogue, and order services. Findings that make Bandit return a non-zero status fail the build; JSON reports are archived even when that happens. The following gates remain documented in the Jenkinsfile but intentionally have no executable stages yet:

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
make validate-catalogue-service
make validate-order-service
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

Order validation installs the order service's pinned dependency set and runs Black,
Ruff, Bandit, its full Pytest suite, offline Alembic graph/SQL validation, a dedicated
Docker build, focused cart/checkout/order frontend tests, and order-service Kustomize
validation. Catalogue validation additionally re-runs the focused inventory reservation
suite and its persistence contract so the checkout dependency remains an explicit gate.

Two live order gates are intentionally separate. Set
`SHOPSPHERE_RUN_ORDER_INTEGRATION=true` only on an agent with the configured PoC context
to run the deployed API Gateway/order smoke validation. Set
`SHOPSPHERE_RUN_ORDER_E2E=true` only for a controlled PoC E2E job; this runs the scenario
suite documented under `tests/end-to-end/order_processing`, including controlled Redis
and Kafka recovery checks, and writes JUnit, JSON, and Markdown evidence. With either
flag unset, Jenkins records `skipped/not applicable` with an environment-dependent
reason. It does not create a passing test result. Enabled suites fail if prerequisites
or validation fail.

The pipeline writes capability status files under `test-results/status`. An enabled
suite is pessimistically marked failed before execution and is reclassified from its
JUnit XML afterward. A report containing only skipped tests becomes
`skipped/not applicable`, not passed; partially skipped reports retain exact passed,
failed, and skipped counts. Disabled live suites are explicitly classified
`skipped/not applicable` with a reason.

Jenkins credentials must be bound as masked environment variables by job configuration. The pipeline never echoes configuration values, credentials, access tokens, or refresh tokens.
