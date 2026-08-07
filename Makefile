.PHONY: help lint test build validate doctor clean

help: ## Show available foundation targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z_-]+:.*## / {printf "%-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

lint: ## Placeholder for Ruff, Black, Bandit, Semgrep, and frontend lint checks
	@echo "lint: placeholder; tooling will be wired in a later delivery day"

test: ## Placeholder for unit, integration, end-to-end, and performance tests
	@echo "test: placeholder; test runners will be wired in a later delivery day"

build: ## Placeholder for reproducible application and container builds
	@echo "build: placeholder; no artifacts were created"

validate: ## Placeholder for Terraform, Kubernetes, policy, and documentation validation
	@echo "validate: placeholder; validators will be wired in a later delivery day"

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
