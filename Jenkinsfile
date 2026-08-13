pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 90, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(
            daysToKeepStr: '30',
            numToKeepStr: '20',
            artifactNumToKeepStr: '10'
        ))
    }

    environment {
        CI_VENV = '.ci/venv'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
        PIP_NO_INPUT = '1'
        NPM_CONFIG_AUDIT = 'false'
        NPM_CONFIG_FUND = 'false'
    }

    stages {
        stage('Checkout') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                checkout scm
            }
        }

        stage('Environment diagnostics') {
            options {
                timeout(time: 3, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Report non-sensitive tool versions', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

printf 'Kernel: '
uname -srm
printf 'Architecture: '
uname -m
python3 --version
node --version
npm --version
docker --version
docker compose version
kubectl version --client=true
kind version
terraform version | sed -n '1p'

docker info >/dev/null 2>&1 || {
    echo 'ERROR: Jenkins cannot access the Docker daemon.' >&2
    exit 1
}
''')
            }
        }

        stage('Repository structure validation') {
            options {
                timeout(time: 3, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Validate required repository paths', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

required_paths=(
    Jenkinsfile
    frontend/package-lock.json
    frontend/package.json
    infrastructure/terraform/versions.tf
    platform/kind/cluster-config.yaml
    platform/kubernetes/overlays/poc/kustomization.yaml
    platform/kubernetes/overlays/poc/order-service/kustomization.yaml
    scripts/validate-order-service-manifests.sh
    scripts/validate-order-migrations.py
    tests/end-to-end/order_processing/run.py
    services/customer-service/pyproject.toml
    services/catalogue-service/pyproject.toml
    services/order-service/pyproject.toml
    services/analytics-service/pyproject.toml
    services/api-gateway/pyproject.toml
)

for path in "${required_paths[@]}"; do
    if [[ ! -e "$path" ]]; then
        echo "ERROR: Required repository path is missing: $path" >&2
        exit 1
    fi
done

git diff --check
echo 'Repository structure validation passed.'
''')
            }
        }

        stage('Integration validation classification') {
            options {
                timeout(time: 2, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Record explicit integration execution policy', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/status

classify_suite() {
    local flag_name="$1"
    local status_file="$2"
    local disabled_reason="${3:-live PoC execution was not enabled}"
    local enabled="${!flag_name:-false}"

    case "$enabled" in
        true)
            printf 'status=skipped/not applicable\nreason=enabled but pipeline stage not yet reached\n' \
                >"$status_file"
            ;;
        false|'')
            printf 'status=skipped/not applicable\nreason=%s\n' \
                "$disabled_reason" >"$status_file"
            ;;
        *)
            echo "ERROR: ${flag_name} must be true or false." >&2
            exit 1
            ;;
    esac
}

classify_suite SHOPSPHERE_RUN_CUSTOMER_INTEGRATION \
    test-results/status/customer-integration.properties
classify_suite SHOPSPHERE_RUN_CATALOGUE_INTEGRATION \
    test-results/status/catalogue-inventory-integration.properties
classify_suite SHOPSPHERE_RUN_ORDER_INTEGRATION \
    test-results/status/order-integration.properties \
    'environment-dependent live PoC order integration was not enabled'
classify_suite SHOPSPHERE_RUN_ORDER_E2E \
    test-results/status/order-e2e.properties \
    'environment-dependent live PoC order E2E execution was not enabled'

echo 'Integration suites are classified explicitly; disabled suites are skipped/not applicable.'
''')
            }
        }

        stage('Customer-service dependency installation') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Install locked customer-service and validation dependencies', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

python3 -m venv "$CI_VENV"
"$CI_VENV/bin/python" -m pip install -e 'services/customer-service[dev]'
"$CI_VENV/bin/python" -m pip check
''')
            }
        }

        stage('Catalogue-service dependency installation') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Install pinned catalogue-service dependencies', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

"$CI_VENV/bin/python" -m pip install -e 'services/catalogue-service[dev]'
"$CI_VENV/bin/python" -m pip check
''')
            }
        }

        stage('Order-service dependency installation') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Install pinned order-service dependencies', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

"$CI_VENV/bin/python" -m pip install -e 'services/order-service[dev]'
"$CI_VENV/bin/python" -m pip check
''')
            }
        }

        stage('Python Black check') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Check Black formatting for every Python service', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

services=(
    services/customer-service
    services/catalogue-service
    services/order-service
    services/analytics-service
    services/api-gateway
)

for service in "${services[@]}"; do
    echo "== Black: $service =="
    (
        cd "$service"
        source_roots=(app tests)
        [[ -d migrations ]] && source_roots+=(migrations)
        checked="$(find "${source_roots[@]}" -type f -name '*.py' -print | wc -l)"
        [[ "$checked" -gt 0 ]] || {
            echo "ERROR: No Python sources were found under $service." >&2
            exit 1
        }
        "$WORKSPACE/$CI_VENV/bin/python" -m black \
            --workers 1 --check --quiet "${source_roots[@]}"
        echo "Black formatting passed for $checked Python files."
    )
done
''')
            }
        }

        stage('Python Ruff linting') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run Ruff for every Python service', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/lint

services=(
    services/customer-service
    services/catalogue-service
    services/order-service
    services/analytics-service
    services/api-gateway
)

for service in "${services[@]}"; do
    service_name="${service##*/}"
    echo "== Ruff: $service =="
    (
        cd "$service"
        "$WORKSPACE/$CI_VENV/bin/python" -m ruff check \
            --output-format=json \
            --output-file="$WORKSPACE/test-results/lint/${service_name}-ruff.json" \
            .
    )
done
''')
            }
        }

        stage('Customer-service Bandit') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Scan customer-service Python code with Bandit', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/security
(
    cd services/customer-service
    "$WORKSPACE/$CI_VENV/bin/python" -m bandit \
        --quiet \
        --recursive app \
        --format json \
        --output "$WORKSPACE/test-results/security/customer-service-bandit.json"
)
''')
            }
        }

        stage('Catalogue-service Bandit') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Scan catalogue-service Python code with Bandit', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/security
(
    cd services/catalogue-service
    "$WORKSPACE/$CI_VENV/bin/python" -m bandit \
        --quiet \
        --recursive app \
        --format json \
        --output "$WORKSPACE/test-results/security/catalogue-service-bandit.json"
)
''')
            }
        }

        stage('Order-service Bandit') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Scan order-service Python code with Bandit', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/security
(
    cd services/order-service
    "$WORKSPACE/$CI_VENV/bin/python" -m bandit \
        --quiet \
        --recursive app \
        --format json \
        --output "$WORKSPACE/test-results/security/order-service-bandit.json"
)
''')
            }
        }

        stage('Python unit tests') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run service unit tests with JUnit output', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/python
services=(
    services/customer-service
    services/catalogue-service
    services/order-service
    services/analytics-service
    services/api-gateway
)

for service in "${services[@]}"; do
    service_name="${service##*/}"
    echo "== Pytest: $service_name =="
    (
        cd "$service"
        "$WORKSPACE/$CI_VENV/bin/python" -m pytest \
            --junitxml="$WORKSPACE/test-results/python/${service_name}.xml"
    )
done
''')
            }
        }

        stage('Catalogue inventory reservation tests') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run focused reservation and persistence contract tests', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/python
cd services/catalogue-service
"$WORKSPACE/$CI_VENV/bin/python" -m pytest \
    tests/test_inventory_reservations.py \
    tests/test_persistence_contract.py::test_reservation_database_contract_enforces_identity_quantity_and_lifecycle \
    --junitxml="$WORKSPACE/test-results/python/catalogue-reservations.xml"
''')
            }
        }

        stage('PoC customer integration tests') {
            when {
                environment name: 'SHOPSPHERE_RUN_CUSTOMER_INTEGRATION', value: 'true'
            }
            options {
                timeout(time: 20, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run opt-in customer identity integration suite', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/integration
status_file='test-results/status/customer-integration.properties'
printf 'status=failed\nreason=integration suite exited unsuccessfully\n' >"$status_file"
"$CI_VENV/bin/python" -m pytest \
    -c tests/integration/pytest.ini \
    tests/integration/customer_identity \
    --junitxml=test-results/integration/customer-identity.xml
"$CI_VENV/bin/python" scripts/classify-junit.py \
    --report test-results/integration/customer-identity.xml \
    --status-file "$status_file"
''')
            }
        }

        stage('PoC catalogue and inventory integration tests') {
            when {
                environment name: 'SHOPSPHERE_RUN_CATALOGUE_INTEGRATION', value: 'true'
            }
            options {
                timeout(time: 20, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run opt-in catalogue and inventory integration suite', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/integration
status_file='test-results/status/catalogue-inventory-integration.properties'
printf 'status=failed\nreason=integration suite exited unsuccessfully\n' >"$status_file"
"$CI_VENV/bin/python" -m pytest \
    -c tests/integration/pytest.ini \
    tests/integration/catalogue_inventory \
    --junitxml=test-results/integration/catalogue-inventory.xml
"$CI_VENV/bin/python" scripts/classify-junit.py \
    --report test-results/integration/catalogue-inventory.xml \
    --status-file "$status_file"
''')
            }
        }

        stage('PoC order capability integration tests') {
            when {
                environment name: 'SHOPSPHERE_RUN_ORDER_INTEGRATION', value: 'true'
            }
            options {
                timeout(time: 20, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run opt-in deployed order capability smoke validation', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/integration
report='test-results/integration/order-capability.xml'
status_file='test-results/status/order-integration.properties'
status='failed'
message='Deployed order capability smoke validation failed.'
if KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}" \
    ./scripts/smoke-test-order-platform.sh; then
    status='passed'
    message='Deployed order capability smoke validation passed through API Gateway.'
fi
"$CI_VENV/bin/python" scripts/write-junit-status.py \
    --report "$report" \
    --suite order-capability-integration \
    --test deployed-order-smoke \
    --status "$status" \
    --message "$message"
"$CI_VENV/bin/python" scripts/classify-junit.py \
    --report "$report" \
    --status-file "$status_file"
[[ "$status" == 'passed' ]]
''')
            }
        }

        stage('PoC order end-to-end tests') {
            when {
                environment name: 'SHOPSPHERE_RUN_ORDER_E2E', value: 'true'
            }
            options {
                timeout(time: 30, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run explicitly enabled live order E2E scenarios', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/end-to-end
status_file='test-results/status/order-e2e.properties'
printf 'status=failed\nreason=end-to-end suite exited unsuccessfully\n' >"$status_file"
"$CI_VENV/bin/python" scripts/write-junit-status.py \
    --report test-results/end-to-end/order-processing.xml \
    --suite order-processing-e2e \
    --test prerequisites \
    --status failed \
    --message 'Order E2E runner did not complete.'
run_status='failed'
if SHOPSPHERE_RUN_ORDER_E2E=true \
    KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}" \
        "$CI_VENV/bin/python" tests/end-to-end/order_processing/run.py; then
    run_status='passed'
fi
"$CI_VENV/bin/python" scripts/classify-junit.py \
    --report test-results/end-to-end/order-processing.xml \
    --status-file "$status_file"
[[ "$run_status" == 'passed' ]]
''')
            }
        }

        stage('Frontend dependency installation') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                dir('frontend') {
                    sh(label: 'Install locked frontend dependencies', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
npm ci --no-audit --no-fund
''')
                }
            }
        }

        stage('Frontend lint') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                dir('frontend') {
                    sh(label: 'Check frontend formatting and lint rules', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
npm run format:check
npm run lint
''')
                }
            }
        }

        stage('Frontend unit test') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run Vitest with JUnit output', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p test-results/frontend
cd frontend
npm test -- \
    --reporter=junit \
    --outputFile="$WORKSPACE/test-results/frontend/vitest.xml"
''')
            }
        }

        stage('Frontend catalogue and inventory tests') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run focused catalogue and inventory frontend tests', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/frontend
cd frontend
npm test -- \
    src/features/catalogue/CatalogueFeature.test.tsx \
    --reporter=junit \
    --outputFile="$WORKSPACE/test-results/frontend/catalogue-inventory.xml"
''')
            }
        }

        stage('Frontend order workflow tests') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run focused cart, checkout, and order frontend tests', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/frontend
cd frontend
npm test -- \
    src/features/orders/OrderFeature.test.tsx \
    src/services/orderApi.test.ts \
    --reporter=junit \
    --outputFile="$WORKSPACE/test-results/frontend/order-workflows.xml"
''')
            }
        }

        stage('Frontend production build') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                dir('frontend') {
                    sh(label: 'Build the production frontend bundle', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
npm run build
''')
                }
            }
        }

        stage('Customer-service Docker build') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Build the customer-service image', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

docker build \
    --label "shopsphere.ci.build=${BUILD_NUMBER}" \
    --tag "shopsphere/customer-service:ci-${BUILD_NUMBER}" \
    services/customer-service
''')
            }
        }

        stage('Catalogue-service Docker build') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Build the catalogue-service image', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

docker build \
    --label "shopsphere.ci.build=${BUILD_NUMBER}" \
    --tag "shopsphere/catalogue-service:ci-${BUILD_NUMBER}" \
    services/catalogue-service
''')
            }
        }

        stage('Order-service Docker build') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Build the order-service image', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

docker build \
    --label "shopsphere.ci.build=${BUILD_NUMBER}" \
    --tag "shopsphere/order-service:ci-${BUILD_NUMBER}" \
    services/order-service
''')
            }
        }

        stage('Remaining Docker image build validation') {
            options {
                timeout(time: 25, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Build all independently deployable images', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

services=(
    services/analytics-service
    services/api-gateway
)

for service in "${services[@]}"; do
    service_name="${service##*/}"
    echo "== Docker build: $service_name =="
    docker build \
        --label "shopsphere.ci.build=${BUILD_NUMBER}" \
        --tag "shopsphere/${service_name}:ci-${BUILD_NUMBER}" \
        "$service"
done

docker build \
    --label "shopsphere.ci.build=${BUILD_NUMBER}" \
    --tag "shopsphere/frontend:ci-${BUILD_NUMBER}" \
    frontend
''')
            }
        }

        stage('Terraform formatting check') {
            options {
                timeout(time: 3, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Check Terraform formatting', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
terraform -chdir=infrastructure/terraform fmt -check -recursive
''')
            }
        }

        stage('Terraform validate') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Initialize without backend and validate Terraform', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
terraform -chdir=infrastructure/terraform init -backend=false -input=false
terraform -chdir=infrastructure/terraform validate
''')
            }
        }

        stage('Kubernetes manifest validation') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Validate kind shape and render PoC manifests', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
make validate-kubernetes
make validate-customer-service
make validate-catalogue-service
make validate-order-service
make validate-api-gateway
''')
            }
        }

        stage('Redis manifest validation') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Validate internal Redis manifests', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
make validate-redis
''')
            }
        }

        stage('Kafka manifest validation') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Validate single-broker KRaft manifests', script: '''#!/usr/bin/env bash
set -Eeuo pipefail
make validate-kafka
''')
            }
        }

        stage('Catalogue database migration integrity') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Validate Alembic graph and compile offline migration SQL', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/migrations
"$CI_VENV/bin/python" scripts/validate-catalogue-migrations.py \
    --report test-results/migrations/catalogue-migration-integrity.json
(
    cd services/catalogue-service
    DATABASE_URL='postgresql+psycopg://validation:validation@127.0.0.1/catalogue_validation' \
        "$WORKSPACE/$CI_VENV/bin/python" -m alembic upgrade head --sql \
        >"$WORKSPACE/test-results/migrations/catalogue-upgrade.sql"
)
''')
            }
        }

        stage('Order database migration integrity') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Validate order Alembic graph and compile offline migration SQL', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p test-results/migrations
"$CI_VENV/bin/python" scripts/validate-order-migrations.py \
    --report test-results/migrations/order-migration-integrity.json
(
    cd services/order-service
    DATABASE_URL='postgresql+psycopg://validation:validation@127.0.0.1/order_validation' \
        "$WORKSPACE/$CI_VENV/bin/python" -m alembic upgrade head --sql \
        >"$WORKSPACE/test-results/migrations/order-upgrade.sql"
)
''')
            }
        }

        stage('Integration validation summary') {
            options {
                timeout(time: 2, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Print passed or skipped integration classifications', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

for status_file in test-results/status/*.properties; do
    capability="${status_file##*/}"
    status="$(sed -n 's/^status=//p' "$status_file")"
    reason="$(sed -n 's/^reason=//p' "$status_file")"
    case "$status" in
        passed|'skipped/not applicable')
            printf '%s: %s (%s)\n' "$capability" "$status" "$reason"
            ;;
        failed)
            echo "ERROR: ${capability}: failed (${reason})" >&2
            exit 1
            ;;
        *)
            echo "ERROR: ${capability} has an unknown validation status." >&2
            exit 1
            ;;
    esac
done
''')
            }
        }

        stage('Archive test results') {
            options {
                timeout(time: 3, unit: 'MINUTES')
            }
            steps {
                junit(
                    testResults: 'test-results/**/*.xml',
                    allowEmptyResults: false,
                    keepLongStdio: true
                )
                archiveArtifacts(
                    artifacts: 'test-results/**/*,docs/evidence/catalogue-inventory-integration-evidence.md,docs/evidence/order-processing-e2e-evidence.md',
                    allowEmptyArchive: false,
                    fingerprint: true
                )
            }
        }
    }

    post {
        unsuccessful {
            // Publish any reports produced before a fail-fast stage stopped the build.
            junit(
                testResults: 'test-results/**/*.xml',
                allowEmptyResults: true,
                keepLongStdio: true
            )
            archiveArtifacts(
                artifacts: 'test-results/**/*,docs/evidence/catalogue-inventory-integration-evidence.md,docs/evidence/order-processing-e2e-evidence.md',
                allowEmptyArchive: true,
                fingerprint: true
            )
        }
        success {
            echo 'Foundation validation completed. No deployment was attempted.'
        }
    }
}

/*
 * PLANNED DEVSECOPS EXPANSION — intentionally not executable in this foundation:
 *
 * Security gates:
 *   - Semgrep static analysis
 *   - Trivy filesystem and container-image scanning
 *   - Python and npm dependency vulnerability scanning
 *   - OPA policy checks for Terraform and Kubernetes artifacts
 *
 * Delivery gates:
 *   - registry publication with provenance
 *   - approval-controlled PoC deployment
 *   - smoke tests, rollback checks, and evidence retention
 *
 * This Jenkinsfile contains no automatic deployment, embedded credential, or
 * service-account key handling. Those controls require separate review.
 */
