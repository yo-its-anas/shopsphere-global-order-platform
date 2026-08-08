PYTHON ?= python3
KUBE_CONTEXT ?= kind-shopsphere-poc
POSTGRESQL_OVERLAY := platform/kubernetes/overlays/poc/postgresql
SERVICE_DIRS := \
	services/customer-service \
	services/catalogue-service \
	services/order-service \
	services/analytics-service \
	services/api-gateway

.PHONY: help format lint test build validate validate-shell validate-kubernetes \
	validate-postgresql postgresql-secret postgresql-apply postgresql-status doctor clean

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

validate: validate-shell validate-kubernetes validate-postgresql ## Run implemented static foundation validation
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
	@kubectl --context "$(KUBE_CONTEXT)" apply -k "$(POSTGRESQL_OVERLAY)"

postgresql-status: ## Run read-only PostgreSQL workload, service, PVC, and database checks
	@KUBE_CONTEXT="$(KUBE_CONTEXT)" ./scripts/check-postgresql.sh

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
