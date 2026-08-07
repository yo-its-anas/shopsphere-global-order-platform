.PHONY: help lint test build validate clean

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

clean: ## Non-destructive placeholder; reports intended cleanup without deleting files
	@echo "clean: no files removed (Day 1 safety placeholder)"
