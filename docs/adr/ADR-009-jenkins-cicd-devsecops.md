# ADR-009: Use Jenkins for CI/CD and DevSecOps orchestration

## Status

Proposed — only the Jenkins responsibility directory exists; no Jenkinsfile, controller, agent, credential, or pipeline run exists.

## Context

The project requires repeatable quality, security, build, infrastructure validation, and deployment gates. Jenkins is part of the mandated stack and can coordinate the required tools from one auditable pipeline.

## Decision

Use pipeline-as-code in Jenkins to orchestrate formatting, linting, automated tests, SAST, dependency and image scanning, Terraform and Kubernetes validation, policy checks, image builds, and controlled PoC deployment. Fail closed on agreed critical gates and retain concise evidence.

## Alternatives considered

- GitHub Actions or GitLab CI: lower controller overhead, but not the mandated orchestration platform.
- Manual scripts: useful as reusable implementation units, but insufficient as auditable CI/CD orchestration.
- Jenkins freestyle jobs: quick initially but less reviewable and reproducible than pipeline-as-code.

## Consequences

Delivery gates become centralized and demonstrable. Jenkins requires secure controller and agent operation, plugin governance, credential management, backups, and maintenance. Pipeline design must avoid one slow global build.

## Security implications

Use least-privilege ephemeral agents where possible, pinned plugins and tools, protected credentials, isolated untrusted builds, signed or attested artifacts, restricted deployment approvals, immutable logs, and no secret output in evidence.

## PoC limitations

The likely single-host controller and agent will not be highly available and may share trust boundaries with workloads. A foundation pipeline exists, but no retained Jenkins controller run or security-scan evidence is present.

## Production evolution

Use a hardened, backed-up controller or managed alternative, ephemeral isolated agents, workload identity, approval segregation, artifact registries, provenance, deployment promotion, disaster recovery, and measured pipeline service levels.

## Viva defence notes

Frame Jenkins as an orchestrator rather than the implementation of every control. Tools such as Ruff, Pytest, Semgrep, Trivy, and OPA perform specialist checks; Jenkins makes their execution repeatable and governed.
