PYTHON ?= python3
KUBE_CONTEXT ?= kind-shopsphere-poc
POSTGRESQL_OVERLAY := platform/kubernetes/overlays/poc/postgresql
KEYCLOAK_OVERLAY := platform/kubernetes/overlays/poc/keycloak
CUSTOMER_SERVICE_OVERLAY := platform/kubernetes/overlays/poc/customer-service
REDIS_OVERLAY := platform/kubernetes/overlays/poc/redis
CATALOGUE_SERVICE_OVERLAY := platform/kubernetes/overlays/poc/catalogue-service
API_GATEWAY_OVERLAY := platform/kubernetes/overlays/poc/api-gateway
KAFKA_OVERLAY := platform/kubernetes/overlays/poc/kafka
CUSTOMER_SERVICE_IMAGE ?= shopsphere/customer-service:poc
CATALOGUE_SERVICE_IMAGE ?= shopsphere/catalogue-service:poc
API_GATEWAY_IMAGE ?= shopsphere/api-gateway:poc
SERVICE_DIRS := \
	services/customer-service \
	services/catalogue-service \
	services/order-service \
	services/analytics-service \
	services/api-gateway

.PHONY: help format lint test build validate validate-shell validate-kubernetes \
	validate-postgresql postgresql-secret postgresql-apply postgresql-status \
	postgresql-reconcile catalogue-service-secret order-service-secret \
	validate-keycloak keycloak-secret keycloak-apply keycloak-configure keycloak-status doctor clean \
	validate-customer-service customer-service-secret customer-service-build \
	customer-service-load customer-service-apply customer-service-status \
	validate-redis redis-secret redis-secret-generate redis-apply redis-status \
	validate-catalogue-service catalogue-service-build catalogue-service-load \
	catalogue-service-apply catalogue-service-status \
	validate-api-gateway api-gateway-build api-gateway-load \
	api-gateway-apply api-gateway-status \
	validate-kafka kafka-apply kafka-topics kafka-status \
	catalogue-event-smoke \
	customer-integration customer-integration-collect \
	catalogue-integration catalogue-integration-collect

help: ## Show available foundation targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z_-]+:.*## / {printf "%-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

format: ## Format and safely organize imports in every Python service
	@set -e; for service in $(SERVICE_DIRS); do \
		echo "== format: $$service =="; \
		(cd "$$service" && $(PYTHON) -m ruff check --fix . && $(PYTHON) -m black --workers 1 .); \
	done

lint: ## Run Ruff, Black, and Bandit for every Python service
	@set -e; for service in $(SERVICE_DIRS); do \
		echo "== lint: $$service =="; \
		(cd "$$service" && $(PYTHON) -m ruff check . && $(PYTHON) -m black --workers 1 --check . && $(PYTHON) -m bandit -q -r app); \
	done

test: ## Run each service's independent Pytest suite
	@set -e; for service in $(SERVICE_DIRS); do \
		echo "== test: $$service =="; \
		(cd "$$service" && $(PYTHON) -m pytest); \
	done

build: ## Build a foundation Docker image for every service
	@set -e; for service in $(SERVICE_DIRS); do \
		name="$${service##*/}"; \
		echo "== build: $$name =="; \
		docker build --tag "shopsphere/$$name:foundation" "$$service"; \
	done

validate: validate-shell validate-kubernetes validate-postgresql validate-keycloak validate-customer-service validate-redis validate-kafka validate-catalogue-service validate-api-gateway ## Run implemented static foundation validation
	@echo "validation: implemented foundation shell and Kubernetes checks passed"

validate-shell: ## Check Bash syntax without executing scripts
	@bash -n scripts/*.sh platform/kind/*.sh

validate-kubernetes: ## Validate the kind shape and render the PoC Kustomize overlay locally
	@command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required" >&2; exit 1; }
	@command -v kind >/dev/null 2>&1 || { echo "kind is required" >&2; exit 1; }
	@test "$$(grep -c '^[[:space:]]*- role:' platform/kind/cluster-config.yaml)" -eq 1
	@grep -q '^[[:space:]]*- role: control-plane$$' platform/kind/cluster-config.yaml
	@kubectl kustomize platform/kubernetes/overlays/poc >/dev/null

validate-postgresql: ## Validate PostgreSQL manifests without changing the cluster
	@./scripts/validate-postgresql-manifests.sh

postgresql-secret: ## Create the PostgreSQL Secret interactively; existing Secrets are preserved
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/create-postgresql-secret.sh

postgresql-apply: validate-postgresql ## Apply the PoC PostgreSQL component; requires its Secret
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-data get secret shopsphere-postgresql-credentials >/dev/null 2>&1 || { \
		echo "Create shopsphere-postgresql-credentials first with 'make postgresql-secret'." >&2; exit 1; }
	@test "$$(kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-data get secret shopsphere-postgresql-credentials -o go-template='{{if index .data "catalogue-password"}}present{{end}}')" = "present" || { \
		echo "Add the catalogue credential first with 'make postgresql-secret'." >&2; exit 1; }
	@test "$$(kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-data get secret shopsphere-postgresql-credentials -o go-template='{{if index .data "order-password"}}present{{end}}')" = "present" || { \
		echo "Add the order-service credential first with 'make postgresql-secret'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" apply -k "$(POSTGRESQL_OVERLAY)"
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-data rollout status statefulset/postgresql --timeout=300s
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/reconcile-postgresql-databases.sh

postgresql-reconcile: ## Idempotently reconcile required logical databases without recreating existing data
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/reconcile-postgresql-databases.sh

catalogue-service-secret: ## Derive the catalogue database URL Secret without displaying credentials
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/create-catalogue-service-secret.sh

order-service-secret: ## Derive the order database URL Secret without displaying credentials
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/create-order-service-secret.sh

postgresql-status: ## Run read-only PostgreSQL workload, service, PVC, and database checks
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/check-postgresql.sh

validate-keycloak: ## Validate Keycloak manifests and realm configuration without changing the cluster
	@./scripts/validate-keycloak-manifests.sh

keycloak-secret: ## Create Keycloak credentials interactively; existing Secrets are preserved
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/create-keycloak-secret.sh

keycloak-apply: validate-keycloak ## Apply the PoC Keycloak component; requires PostgreSQL and its Secret
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-platform get secret shopsphere-keycloak-credentials >/dev/null 2>&1 || { \
		echo "Create shopsphere-keycloak-credentials first with 'make keycloak-secret'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-data get service postgresql >/dev/null 2>&1 || { \
		echo "The internal PostgreSQL Service is required before Keycloak can be applied." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" apply -k "$(KEYCLOAK_OVERLAY)"

keycloak-configure: ## Reconcile Keycloak client policies and the least-privilege activity reader
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/configure-keycloak.sh

keycloak-status: ## Run non-destructive Keycloak workload, realm, client, event, and database checks
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/check-keycloak.sh

validate-customer-service: ## Validate customer-service manifests without changing the cluster
	@./scripts/validate-customer-service-manifests.sh

customer-service-secret: ## Derive the customer database URL Secret without displaying credentials
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/create-customer-service-secret.sh

customer-service-build: ## Build the local customer-service PoC image
	@docker build --tag "$(CUSTOMER_SERVICE_IMAGE)" services/customer-service

customer-service-load: ## Load the existing customer-service image into the kind node
	@./platform/kind/load-images.sh "$(CUSTOMER_SERVICE_IMAGE)"

customer-service-apply: validate-customer-service ## Apply the internal customer-service workload; requires runtime Secrets
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps get secret shopsphere-customer-service-database >/dev/null 2>&1 || { \
		echo "Create shopsphere-customer-service-database first with 'make customer-service-secret'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps get secret shopsphere-customer-activity-keycloak >/dev/null 2>&1 || { \
		echo "Reconcile shopsphere-customer-activity-keycloak first with 'make keycloak-configure'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" apply -k "$(CUSTOMER_SERVICE_OVERLAY)"

customer-service-status: ## Run read-only customer-service workload, probe, and exposure checks
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/check-customer-service.sh

validate-redis: ## Validate Redis manifests without changing the cluster
	@./scripts/validate-redis-manifests.sh

redis-secret: ## Create Redis runtime Secrets through hidden interactive input
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/create-redis-secret.sh

redis-secret-generate: ## Explicitly generate Redis runtime Secrets without displaying values
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/create-redis-secret.sh --generate

redis-apply: validate-redis ## Apply the internal PoC Redis cache; requires runtime Secrets
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-data get secret shopsphere-redis-credentials >/dev/null 2>&1 || { \
		echo "Create Redis runtime Secrets first with 'make redis-secret' or 'make redis-secret-generate'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps get secret shopsphere-catalogue-cache >/dev/null 2>&1 || { \
		echo "Create Redis runtime Secrets first with 'make redis-secret' or 'make redis-secret-generate'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" apply -k "$(REDIS_OVERLAY)"
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-data rollout status deployment/redis --timeout=180s

redis-status: ## Verify Redis readiness, authentication, and internal exposure
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/check-redis.sh

validate-catalogue-service: ## Validate catalogue-service manifests without changing the cluster
	@./scripts/validate-catalogue-service-manifests.sh

catalogue-service-build: ## Build the cache-enabled catalogue-service PoC image
	@docker build --tag "$(CATALOGUE_SERVICE_IMAGE)" services/catalogue-service

catalogue-service-load: ## Load the existing catalogue-service image into the kind node
	@./platform/kind/load-images.sh "$(CATALOGUE_SERVICE_IMAGE)"

catalogue-service-apply: validate-catalogue-service ## Apply the internal catalogue-service workload
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps get secret shopsphere-catalogue-service-database >/dev/null 2>&1 || { \
		echo "Create the catalogue database Secret first with 'make catalogue-service-secret'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps get secret shopsphere-catalogue-cache >/dev/null 2>&1 || { \
		echo "Create Redis runtime Secrets first with 'make redis-secret' or 'make redis-secret-generate'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-data get service redis >/dev/null 2>&1 || { \
		echo "Apply Redis first with 'make redis-apply'." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" apply -k "$(CATALOGUE_SERVICE_OVERLAY)"
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps rollout status deployment/catalogue-service --timeout=300s

catalogue-service-status: ## Verify catalogue-service health, Redis connectivity, and internal exposure
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/check-catalogue-service.sh

validate-api-gateway: ## Validate API Gateway manifests without changing the cluster
	@./scripts/validate-api-gateway-manifests.sh

api-gateway-build: ## Build the internal API Gateway PoC image
	@docker build --tag "$(API_GATEWAY_IMAGE)" services/api-gateway

api-gateway-load: ## Load the existing API Gateway image into the kind node
	@./platform/kind/load-images.sh "$(API_GATEWAY_IMAGE)"

api-gateway-apply: validate-api-gateway ## Apply the internal API Gateway after its upstream services
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps get service customer-service >/dev/null 2>&1 || { \
		echo "Deploy customer-service before the API Gateway." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps get service catalogue-service >/dev/null 2>&1 || { \
		echo "Deploy catalogue-service before the API Gateway." >&2; exit 1; }
	@kubectl --context "$(KUBE_CONTEXT)" apply -k "$(API_GATEWAY_OVERLAY)"
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-apps rollout status deployment/api-gateway --timeout=180s

api-gateway-status: ## Verify API Gateway readiness, exposure, and catalogue forwarding
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/check-api-gateway.sh

validate-kafka: ## Validate the single-broker KRaft manifests without changing the cluster
	@./scripts/validate-kafka-manifests.sh

kafka-apply: validate-kafka ## Apply the internal single-broker Kafka PoC
	@kubectl --context "$(KUBE_CONTEXT)" apply -f platform/kubernetes/base/resource-quotas.yaml
	@kubectl --context "$(KUBE_CONTEXT)" apply -k "$(KAFKA_OVERLAY)"
	@kubectl --context "$(KUBE_CONTEXT)" -n shopsphere-platform rollout status statefulset/kafka --timeout=420s

kafka-topics: ## Idempotently create and configure governed domain-event topics
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/reconcile-kafka-topics.sh

kafka-status: ## Verify broker readiness, internal exposure, storage, and topics
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/check-kafka.sh

catalogue-event-smoke: ## Create simulated catalogue changes and verify producer input safely
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/smoke-test-catalogue-events.sh

customer-integration: ## Run opt-in live customer capability integration tests with JUnit output
	@mkdir -p test-results/integration
	@$(PYTHON) -m pytest -c tests/integration/pytest.ini \
		tests/integration/customer_identity \
		--junitxml=test-results/integration/customer-identity.xml

customer-integration-collect: ## Collect customer integration tests without contacting services
	@$(PYTHON) -m pytest -c tests/integration/pytest.ini \
		tests/integration/customer_identity --collect-only

catalogue-integration: ## Run opt-in catalogue/inventory integration tests with JUnit output
	@mkdir -p test-results/integration
	@$(PYTHON) -m pytest -c tests/integration/pytest.ini \
		tests/integration/catalogue_inventory \
		--junitxml=test-results/integration/catalogue-inventory.xml

catalogue-integration-collect: ## Collect catalogue/inventory integration tests without services
	@$(PYTHON) -m pytest -c tests/integration/pytest.ini \
		tests/integration/catalogue_inventory --collect-only

doctor: ## Run non-destructive host and tool checks
	@status=0; \
	for check in \
		scripts/check-host.sh \
		scripts/check-docker.sh \
		scripts/check-kubernetes-tools.sh \
		scripts/check-terraform.sh \
		scripts/check-jenkins.sh; do \
		echo "== $$check =="; \
		"./$$check" || status=1; \
	done; \
	./scripts/capture-tool-versions.sh || status=1; \
	exit $$status

clean: ## Non-destructive placeholder; reports intended cleanup without deleting files
	@echo "clean: no files removed (non-destructive safety placeholder)"
