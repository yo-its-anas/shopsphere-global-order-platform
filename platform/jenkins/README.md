# ShopSphere Complete CI/CD & DevSecOps Jenkins Pipeline

This document outlines the architecture, stages, security policies, and credential requirements for the upgraded ShopSphere monorepo Jenkins pipeline.

## 1. Upgraded Pipeline Stages

Our declarative pipeline is fully configured with an automated checkout, environment checks, full static quality gates, automated testing, container image builds, deployment to a local single-node `kind` cluster, integration/E2E tests, and rollbacks on failure.

### 1.1 SOURCE
*   **Checkout:** Fetches the repository from source control.
*   **Environment Diagnostics & Repository Validation:** Verifies client versions (`docker`, `kubectl`, `kind`, `terraform`, etc.) and ensures all critical monorepo directory structures and configurations are completely intact.

### 1.2 SOFTWARE QUALITY
*   **Python Formatting & Ruff Linting:** Ensures styling checks (Black) and rigorous static rules (Ruff) pass for all 5 microservices (`customer-service`, `catalogue-service`, `order-service`, `analytics-service`, `api-gateway`).
*   **Frontend Linting:** Enforces Prettier formatting checks and ESLint rules.

### 1.3 AUTOMATED TESTING
*   **Python Unit Tests:** Executes individual Pytest test suites with separate JUnit XML outputs for all 5 services.
*   **Frontend Unit & Component Tests:** Performs complete Vitest execution alongside targeted feature suites with full JUnit XML generation.

### 1.4 SECURE SOFTWARE DEVELOPMENT
*   **Bandit Static Scan:** Evaluates customer, catalogue, and order service code bases with automated JSON security audits.
*   **Semgrep Static Analysis:** Evaluates the monorepo recursively for advanced code vulnerabilities using the standard containerized `returntocorp/semgrep` image.

### 1.5 BUILD
*   **Container Image Builds:** Compiles Docker container images sequentially for `customer-service`, `catalogue-service`, `order-service`, `analytics-service`, `api-gateway`, and `frontend`, tagging each image with `ci-${BUILD_NUMBER}`.

### 1.6 CONTAINER SECURITY
*   **Trivy File System Scanning:** Evaluates the workspace directory for vulnerabilities using `aquasec/trivy`.
*   **Trivy Image Scanning:** Recursively scans newly built service container images to prevent CVE leakage before cluster deployment.

### 1.7 INFRASTRUCTURE VALIDATION
*   **Terraform Validation:** Verifies Terraform code formatting recursively and initializes providers safely using `-backend=false` to execute static safety audits offline.
*   **Kubernetes Manifest Validation:** Uses Kustomize and Kubeval/kubectl-Kustomize utilities to statically validate cluster bases and overlay environments, covering all application, database, logging (Loki, Promtail), monitoring (Prometheus, Grafana), and security (Wazuh-manager, Wazuh-agent) manifests.

### 1.8 POLICY AS CODE
*   **OPA policy compliance:** Evaluates rendered Kubernetes manifests against custom Rego rules (`platform/security/rego/security.rego`) to ensure no forbidden security configurations exist (such as privileged containers in core namespaces).

### 1.9 INTEGRATION & DEPLOYMENT
*   **PoC Deployment to kind:** Automatically loads built container images directly into the local `kind` cluster using the `load-images.sh` script, patches overlay configurations to use the newly built image tags, deploys to Kubernetes, and monitors rollout status until 100% ready.
*   **Integration Tests:** Conditionally executes Keycloak and database-level integration suites when opt-in variables are deliberately set.

### 1.10 POST DEPLOYMENT & REPORTING
*   **Smoke Validation:** Executes `./scripts/smoke-test-order-platform.sh` to send active traffic through the API Gateway, validating real-world transactions.
*   **Rollback on Failure:** The pipeline includes a strict `post.failure` catch block. If any stage or rollout status fails or times out, it automatically triggers a safe, non-destructive rollback using `kubectl rollout undo` on all core microservices to revert to the previous working deployment revision instantly.
*   **Evidence Archiving:** Publishes overall test summaries in the Jenkins UI via JUnit and archives all machine-readable security reports.

---

## 2. Security Gate Severity Policy

To ensure high technical integrity, ShopSphere enforces a strict automated security gate policy:

*   **Failure Threshold:** Any security finding flagged as `CRITICAL` or `HIGH` by Bandit, Semgrep, Trivy, or OPA will automatically fail the pipeline build.
*   **Zero Silent Ignores:** All security exceptions must be explicitly recorded in `platform/security/suppressions.json`.
*   **Audit-Ready Suppressions:** Every suppression requires a recorded rule identifier, a comprehensive engineering justification explaining the mitigation or false-positive nature of the finding, and an active expiration date.

---

## 3. Jenkins Credentials Setup & Bindings

To prevent hard-coded secrets, credentials must be registered in the Jenkins Global Credentials Store and mapped securely using Jenkins environment bindings:

1.  **PostgreSQL Credentials:**
    *   **Name inside Jenkins:** `postgres-admin-credentials` (stored as secret text)
    *   **Environment variable:** `PGPASSWORD`
2.  **Keycloak Client Credentials:**
    *   **Name inside Jenkins:** `keycloak-smoke-client-secret` (stored as secret text)
    *   **Environment variable:** `KEYCLOAK_CLIENT_SECRET`
3.  **Kubernetes Config:**
    *   **Name inside Jenkins:** `kind-kubeconfig` (stored as a secure file)
    *   **Environment variable:** `KUBECONFIG` (loaded via `withCredentials([file(credentialsId: 'kind-kubeconfig', variable: 'KUBECONFIG')])`)

*Note: The pipeline strictly masks all environment variables, ensuring no tokens, passwords, or client secrets are ever echoed or printed to console output logs.*
