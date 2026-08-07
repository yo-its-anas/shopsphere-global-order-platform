.PHONY: help lint test build validate validate-shell validate-kubernetes doctor clean

help: ## Show available foundation targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z_-]+:.*## / {printf "%-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

lint: ## Placeholder for Ruff, Black, Bandit, Semgrep, and frontend lint checks
	@echo "lint: placeholder; tooling will be wired in a later delivery day"

test: ## Placeholder for unit, integration, end-to-end, and performance tests
	@echo "test: placeholder; test runners will be wired in a later delivery day"

build: ## Placeholder for reproducible application and container builds
	@echo "build: placeholder; no artifacts were created"

validate: validate-shell validate-kubernetes ## Run implemented static foundation validation
	@echo "validation: implemented Day 1 shell and Kubernetes checks passed"

validate-shell: ## Check Bash syntax without executing scripts
	@bash -n scripts/*.sh platform/kind/*.sh

validate-kubernetes: ## Validate the kind shape and render the PoC Kustomize overlay locally
	@command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required" >&2; exit 1; }
	@command -v kind >/dev/null 2>&1 || { echo "kind is required" >&2; exit 1; }
	@test "$$(grep -c '^[[:space:]]*- role:' platform/kind/cluster-config.yaml)" -eq 1
	@grep -q '^[[:space:]]*- role: control-plane$$' platform/kind/cluster-config.yaml
	@kubectl kustomize platform/kubernetes/overlays/poc >/dev/null

doctor: ## Run non-destructive Day 1 host and tool checks
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
	@echo "clean: no files removed (Day 1 safety placeholder)"
