# ShopSphere Platform Master Documentation Index

This document acts as the global directory index for all version-controlled documentation, guides, operational runbooks, capability architectural designs, and compliance audit reports within the ShopSphere Global repository.

---

## 1. Operating Guides & Runbooks
*   📖 [Installation Guide](guides/installation.md) — Step-by-step local environment and virtualized cluster dependency configuration.
*   📖 [Deployment Guide](guides/deployment.md) — Jenkins 23-stage declarative pipeline workflows, rollback policies, and cold-start bootstrap guides.
*   📖 [User Guide](guides/customer-self-service.md) — Comprehensive runbook for customer actions: login, profile, cart management, checkout, and history.
*   📖 [Administrator Guide](guides/order-processing-administration.md) — Runbook for Keycloak CLI management, outbox/offset audits, and metrics diagnostics.
*   📖 [Backup & Recovery Guide](guides/backup-and-recovery.md) — Secure database, identity, and telemetry backup schedules.
*   📖 [Troubleshooting Guide](guides/troubleshooting.md) — Remediation steps for network timeout, login, container crash, and schema conflicts.

---

## 2. Structural Architecture Maps (Mermaid)
*   🖼️ [System Architecture Maps](architecture/system-architecture-maps.md) — Enterprise Software, High-Level Solution, Detailed System (Namespaces), and API Gateway Ingress maps.
*   🖼️ [Network & Data Flows](architecture/network-and-data-flows.md) — Private Network topology, Network Flow sequence ( Golden Signals), Level 0 & Level 1 Data Flows, internal code Components, and domain Class UMLs.
*   🖼️ [Workflows, Pipelines, & ERDs](architecture/workflows-pipelines-and-database.md) — Synchronous Checkout sequence, Jenkins CI/CD pipeline structures, DevSecOps shift-left checkpoints, and relational database ERDs.
*   🖼️ [Recommended Production Architecture](architecture/production/recommended-enterprise-architecture.md) — Cloud-scale multi-zone GKE blueprints, Cloud SQL HA replication, and a side-by-side comparison with the PoC.

---

### 4.3 Quality, Standards & Compliance Audit Reports
*   ✅ [Capstone Compliance Audit](assessment/compliance-audit.md) — Full requirements verification matrix.
*   ✅ [Submission Integrity Audit](assessment/submission-integrity-audit.md) — Architectural and documentation consistency audit.
*   ✅ [Final Pre-Submission Validation Report](assessment/final-readiness-report.md) — SRE pre-submission readiness verification.
*   ✅ [International Standards Alignment](standards/international-standards-alignment.md) — Mapped alignment with ISO 12207, ISO 25010, ISO 27001, NIST SSDF, NIST CSF 2.0, OWASP Top 10, OWASP ASVS, CIS, COBIT, and ITIL 4 frameworks.
*   ✅ [SRE Observability Validation Report](evidence/formal-validation-report.md) — Live metrics scraping, Loki log ingest, and failure alert testing log evidence.
*   ✅ [Performance Baseline Report](tests/performance/performance_report.md) — Concurrent transaction latency percentiles ($p_{50}, p_{95}, p_{99}$).
*   ✅ [Viva Architecture Defense Pack](viva/architecture-defense.md) — SRE Socratic questions, short/deep defenses, and trade-off matrices for your panel review.

