# Operational Security and DevSecOps Platform

This directory owns future Wazuh, Semgrep, Trivy, and OPA configuration. Application
identity/RBAC remains owned by Keycloak and backend services; application performance
monitoring remains owned by the observability platform.

The security-monitoring boundary is defined in the
[Executive Operations and Observability Architecture](../../docs/architecture/observability-architecture.md),
[ADR-009](../../docs/adr/ADR-009-jenkins-cicd-devsecops.md), and
[SECURITY.md](../../SECURITY.md).

## Current implementation state

No Wazuh deployment/agent policy, Semgrep ruleset, Trivy configuration, scan report, OPA
policy bundle, policy decision, or enforcement evidence is committed here. Bandit is an
active Jenkins stage for customer-service, catalogue-service, and order-service. Black,
Ruff, Pytest, frontend checks, Docker builds, Terraform validation, and Kubernetes
validation also exist, but they do not make the prescribed security platform complete.

## Control boundaries

| Control | Responsibility |
| --- | --- |
| Wazuh | Runtime Ubuntu host/security activity, carefully scoped file integrity, selected authentication/runtime security events, and future SIEM forwarding |
| Semgrep | Cross-language SAST and organization-specific secure-coding rules in Jenkins |
| Trivy | Filesystem/dependency, built-image, and IaC misconfiguration/vulnerability scanning |
| OPA | Reviewable policy decisions for rendered Kubernetes, Terraform, image provenance, and deployment admission intent |
| Bandit | Python-specific security anti-pattern scanning already configured in Jenkins |

Wazuh does not replace Prometheus, Grafana, Loki, OpenTelemetry, Keycloak, or domain audit
records. Semgrep/Trivy/OPA do not replace tests, code review, runtime authorization, or
incident response.

## Planned repository rules

- Pin or version policy/rule sources and record their origin.
- Define severity thresholds, fail behavior, exception owner, justification, and expiry.
- Archive machine-readable reports only after checking that paths/content reveal no
  secrets.
- Scan built image digests rather than an ambiguous mutable tag when promotion exists.
- Use OPA to reject privileged/root workloads, missing probes/limits, public data-service
  exposure, dangerous host mounts/capabilities, and unapproved image sources.
- Keep Wazuh enrollment keys, manager credentials, webhook URLs, allow-lists, and runtime
  secrets outside Git.
- Exclude PostgreSQL/Kafka/Redis data, container layers, build caches, logs, and Secret
  paths from broad file-integrity monitoring.

## PoC and production boundary

A Wazuh component placed on the same VM cannot independently report complete host loss
and shares the workload failure/security domain. The PoC may demonstrate host events and
file integrity, but must not claim centralized SIEM resilience.

Production should use independently available centralized security monitoring/SIEM,
protected agent enrollment, workload identity, private management access, multi-zone
retention, governed identity-event export, alert routing, incident runbooks, and audited
policy/exception management.
