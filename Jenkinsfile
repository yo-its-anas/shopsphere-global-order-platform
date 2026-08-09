pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
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

        stage('Python formatting check') {
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Prepare Python CI environment and check Black formatting', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

python3 -m venv "$CI_VENV"
"$CI_VENV/bin/python" -m pip install -e 'services/customer-service[dev]'

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
        "$WORKSPACE/$CI_VENV/bin/python" -m black --workers 1 --check app tests
    )
done
''')
            }
        }

        stage('Python linting') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Run Ruff for every Python service', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

services=(
    services/customer-service
    services/catalogue-service
    services/order-service
    services/analytics-service
    services/api-gateway
)

for service in "${services[@]}"; do
    echo "== Ruff: $service =="
    (
        cd "$service"
        "$WORKSPACE/$CI_VENV/bin/python" -m ruff check .
    )
done
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

        stage('Customer capability integration tests') {
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
"$CI_VENV/bin/python" -m pytest \
    -c tests/integration/pytest.ini \
    tests/integration/customer_identity \
    --junitxml=test-results/integration/customer-identity.xml
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

        stage('Docker image build validation') {
            options {
                timeout(time: 25, unit: 'MINUTES')
            }
            steps {
                sh(label: 'Build all independently deployable images', script: '''#!/usr/bin/env bash
set -Eeuo pipefail

services=(
    services/customer-service
    services/catalogue-service
    services/order-service
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
                    artifacts: 'test-results/**/*.xml',
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
                artifacts: 'test-results/**/*.xml',
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
 *   - Bandit Python security scanning
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
