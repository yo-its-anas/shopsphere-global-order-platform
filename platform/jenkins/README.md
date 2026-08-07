# Jenkins Day 1 Pipeline Foundation

The root `Jenkinsfile` defines the initial validation pipeline for the ShopSphere monorepo. It is deliberately a Day 1 quality foundation, not the final Day 5 DevSecOps or deployment implementation.

## Pipeline behavior

The declarative pipeline uses one Jenkins workspace and executes these stages sequentially with fail-fast shell behavior:

1. Explicit source checkout.
2. Non-sensitive host and tool diagnostics.
3. Required monorepo path and Git whitespace validation.
4. Isolated Python virtual environment preparation and Black checks.
5. Ruff linting for all five Python services.
6. Pytest unit tests for all five services with individual JUnit XML reports.
7. Locked frontend installation using `npm ci`.
8. Frontend Prettier and ESLint checks.
9. Vitest execution with JUnit XML output.
10. Docker builds for the five backend images and the frontend image.
11. Terraform formatting validation.
12. Terraform provider initialization with `-backend=false` and configuration validation.
13. Offline kind-shape and PoC Kustomize rendering validation.
14. JUnit publication and test-result archival.

The pipeline has a 60-minute overall timeout plus tighter stage timeouts, timestamps, disabled concurrent runs, and retention of 20 builds for at most 30 days. A failure stops subsequent stages. If failure occurs after any test report is created, the pipeline-level `post` handler attempts to publish and archive that partial evidence.

## Agent prerequisites

The Jenkins agent must provide:

- Bash, Git, Python 3 with `venv`, Node.js 20.19 or later, and npm;
- Docker CLI, Compose plugin, Buildx, and permission for the Jenkins identity to use the Docker daemon;
- kubectl and kind;
- Terraform compatible with `infrastructure/terraform/versions.tf`;
- outbound access to the approved Python, npm, Terraform-provider, and container registries.

The agent must not solve missing access with `sudo`, a privileged container, a world-writable Docker socket, or embedded credentials. Registry and cloud identities will require reviewed Jenkins credential bindings in a later phase; none are configured here.

Docker validation creates locally tagged `ci-<build number>` images. Host-level image retention and garbage collection are an administrator responsibility and are intentionally not implemented as destructive pipeline cleanup.

## Explicit non-goals

- No application, infrastructure, kind, Kubernetes, or cloud deployment.
- No Terraform plan or apply.
- No cluster creation or deletion.
- No image publication.
- No authentication or secret retrieval.
- No claim that DevSecOps controls are complete.

## Planned Day 5 expansion

The following gates are documented in the Jenkinsfile but intentionally have no executable stages yet:

- Bandit;
- Semgrep;
- Trivy filesystem and image scanning;
- Python and npm dependency scanning;
- OPA policy checks;
- artifact provenance and registry publication;
- approval-controlled PoC deployment, smoke testing, and rollback validation.

Day 5 implementation must define severity thresholds, false-positive governance, credential bindings, evidence retention, approval boundaries, and failure behavior before any gate or deployment becomes active.

## Local command alignment

The pipeline uses the same repository-level building blocks available to developers:

```bash
make validate-kubernetes
terraform -chdir=infrastructure/terraform fmt -check -recursive
terraform -chdir=infrastructure/terraform init -backend=false -input=false
terraform -chdir=infrastructure/terraform validate
```

Python commands execute inside an ephemeral workspace virtual environment. Frontend commands execute inside `frontend/` against the committed `package-lock.json`.
