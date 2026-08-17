# International Standards Alignment Matrix

This document provides a formal mapping of the ShopSphere Global Enterprise Platform PoC against international software engineering, security, and operational standards. 

> **GOVERNANCE DISCLAIMER**
> 
> **SHOPSPHERE GLOBAL DOES NOT CLAIM FORMAL CERTIFICATION, COMPLIANCE, OR ACCREDITATION WITH ANY REPRESENTED STANDARD.**
>
> All mappings are conceptual. The platform has been *influenced by*, *considered*, *partially aligned with*, or *partially demonstrated* these standards inside a single-node sandbox Proof-of-Concept (PoC) environment.

---

## 1. Standards Alignment Matrix

### 1.1 Software Lifecycle & Requirements

#### ISO/IEC 12207:2017 (Systems and software engineering — Software life cycle processes)
*   **Principle / Control Area:** Technical Processes (Section 6.4) — Requirements Definition, Design Definition, System Analysis, Implementation, Integration, and Verification.
*   **ShopSphere Alignment:** *Partially demonstrated* via our systematic multi-service design. The software development lifecycle is governed by automated verification gates.
*   **Evidence Location:** `Jenkinsfile` (quality gates), `docs/requirements-traceability.md`, and capability specifications under `docs/architecture/`.
*   **Limitation / Gap:** The PoC operates under a single-node virtualization sandbox, omitting multi-zone GKE deployment and formal production stage gates.

#### ISO/IEC 25010:2011 (Systems and software quality models)
*   **Principle / Control Area:** Software Product Quality Model — Functional Suitability, Performance Efficiency, Security, Maintainability, and Reliability.
*   **ShopSphere Alignment:** *Aligned with* performance baseline benchmarks (tests/performance), maintainability (Ruff/Black styling checks), and security validation sweeps.
*   **Evidence Location:** `tests/performance/performance_report.md` (latency profiling) and `/test-results/lint/` (code analysis).
*   **Limitation / Gap:** Reliability is constrained to pod-level restarts; no physical node-level failover or high availability is implemented in the PoC.

#### ISO/IEC 29148:2018 (Systems and software engineering — Life cycle processes — Requirements engineering)
*   **Principle / Control Area:** Requirements Traceability — Maintaining complete bidirectional traceability from system requirements to code and test cases.
*   **ShopSphere Alignment:** *Partially demonstrated* via the core traceability index, mapping functional capstone requirements to concrete services, schemas, and test specs.
*   **Evidence Location:** `docs/requirements-traceability.md`.
*   **Limitation / Gap:** Traceability mappings are compiled manually by SREs rather than linked dynamically to issue-tracking software (e.g., Jira).

---

### 1.2 Information Security & Secure Coding

#### ISO/IEC 27001:2022 (Information security, cybersecurity and privacy protection)
*   **Principle / Control Area:** Control A.8.20 (Network Security), A.8.24 (Use of Cryptography), A.8.28 (Secure Coding), and A.5.15 (Access Control).
*   **ShopSphere Alignment:** *Influenced by* cryptography (RS256 JWT signatures), access control (Keycloak RBAC), and network security (Kubernetes private namespaces and NetworkPolicies).
*   **Evidence Location:** `platform/kubernetes/base/keycloak/`, `api-gateway/app/core/security.py`, and Cilium/Calico NetworkPolicies.
*   **Limitation / Gap:** Key management is not offloaded to an HSM/KMS (e.g., Google KMS); secrets are stored in standard base64-encoded Kubernetes Secrets (not integrated with Vault).

#### NIST Secure Software Development Framework (SSDF) v1.1 (SP 800-218)
*   **Principle / Control Area:** Produce Secure Software (PW) & Respond to Vulnerabilities (RV) — Reviewing code, scanning third-party dependencies, and testing configurations statically.
*   **ShopSphere Alignment:** *Aligned with* shift-left DevSecOps. Bandit, Semgrep, and Trivy filesystem/image scanners run on every git push via Jenkins, preventing vulnerable packages from reaching pods.
*   **Evidence Location:** `Jenkinsfile` (stages 8, 9, 12, 13) and `platform/security/suppressions.json`.
*   **Limitation / Gap:** Suppressions are manually configured on-disk rather than dynamically approved via a centralized security dashboard.

#### NIST Cybersecurity Framework (CSF) 2.0
*   **Principle / Control Area:** Protect (PR) & Detect (DE) — Identity Management, Access Control, Data Security, and active Security Continuous Monitoring.
*   **ShopSphere Alignment:** *Partially demonstrated* via centralized Keycloak OIDC authentication (Protect) and active container SIEM audits via Wazuh (Detect).
*   **Evidence Location:** `docs/architecture/wazuh-security-monitoring.md` and Keycloak realm files.
*   **Limitation / Gap:** Anomalies are logged locally on-disk (`alerts.json`) but lack automatic log forwarding to an external SOC or security alerting platform (e.g., PagerDuty).

#### OWASP Top 10 (2021)
*   **Principle / Control Area:** Broken Access Control (A01), Cryptographic Failures (A02), Injection (A03), and Security Misconfigurations (A05).
*   **ShopSphere Alignment:** *Aligned with* secure coding practices:
    *   *Access Control:* Derived from Keycloak JWT claims, preventing IDOR.
    *   *Injection:* Fully parameterized SQL queries executed via SQLAlchemy.
    *   *Misconfiguration:* Automated OPA policies block privileged container overrides in manifests.
*   **Evidence Location:** `services/order-service/app/api/v1/orders.py` (access validation), `platform/security/rego/security.rego`, and database repositories.
*   **Limitation / Gap:** Rate limiting is not globally enforced at the API Gateway.

#### OWASP ASVS v4.0.3 (Application Security Verification Standard)
*   **Principle / Control Area:** Level 1 Verification — Authentication (V2), Session Management (V3), Access Control (V4), Validation (V5), and Error Handling (V7).
*   **ShopSphere Alignment:** *Partially demonstrated* via Bearer JWT signature checks, input schema verification using Pydantic models, and customized safe error envelopes.
*   **Evidence Location:** `services/customer-service/app/schemas/customer.py` (Pydantic validation) and `app/core/exceptions.py`.
*   **Limitation / Gap:** Does not include automated SAST integration specifically mapped to ASVS verification numbers.

#### OWASP SAMM v2.0 (Software Assurance Maturity Model)
*   **Principle / Control Area:** Verification (Design Review, Security Testing) & Governance (Strategy & Metrics).
*   **ShopSphere Alignment:** *Influenced by* automated security scoring. High/Critical findings from Trivy and Semgrep act as quality gates to fail builds automatically.
*   **Evidence Location:** `Jenkinsfile` and `platform/security/suppressions.json`.
*   **Limitation / Gap:** The PoC lacks formal application security training or developer metrics tracked over time.

#### CIS Critical Security Controls v8
*   **Principle / Control Area:** Control 3 (Data Protection), Control 5 (Account Monitoring), Control 6 (Access Control Management), and Control 16 (Application Software Security).
*   **ShopSphere Alignment:** *Partially demonstrated* via least-privilege service accounts (`order-service-identity`), read-only hostPaths, and encrypted communications.
*   **Evidence Location:** `scripts/reconcile-order-service-identity.sh` and Kubernetes manifests.
*   **Limitation / Gap:** The PoC environment utilizes a shared host kernel and shared virtualized networking without complete cloud node-pool separation.

---

### 1.3 Service Management & Governance

#### COBIT 2019 (Control Objectives for Information and Related Technologies)
*   **Principle / Control Area:** Managed Configuration (BAI09), Managed Changes (BAI06), Managed Operations (DSS01), and Managed Security (DSS05).
*   **ShopSphere Alignment:** *Considered* via comprehensive version control. All application states, cluster configurations, pipelines, and schema migrations are stored as versioned, declarative Git code.
*   **Evidence Location:** Complete Git commit history, `Alembic` migration trees, and Kustomize overlays.
*   **Limitation / Gap:** No formal Change Advisory Board (CAB) workflow or operational ticketing integration (e.g., ServiceNow).

#### ITIL 4 (Information Technology Infrastructure Library)
*   **Principle / Control Area:** Service Design, Service Transition (Change Enablement, Release Management), and Service Operation (Incident Management, Monitoring & Event Management).
*   **ShopSphere Alignment:** *Aligned with* release management and event monitoring. Prometheus and Loki actively scrape cluster states to generate metrics, and Jenkins automates safe rollbacks on failure.
*   **Evidence Location:** `docs/architecture/observability-architecture.md` and the `post.failure` rollback blocks in `Jenkinsfile`.
*   **Limitation / Gap:** Incident management is manual; the PoC has no automatic integration with on-call paging rotations (e.g., PagerDuty).

---

## 2. Viva Panel Review Summary

*How international standards directly influenced the ShopSphere platform architecture:*

### 2.1 Architecture & Design (ISO/IEC 12207 & ISO/IEC 29148)
*   **Standard Influence:** Enforced bidirectional requirements-to-implementation traceability, mapping functional requirements to localized service owners and verification scripts. 
*   **Defense Line:** "We decoupled bounded contexts at the database level to satisfy 12207's structural modularity criteria. This prevents schema changes in Catalogue from ever breaking transactional processes in Order."

### 2.2 Secure Coding & Access Control (OWASP Top 10 & ISO/IEC 27001)
*   **Standard Influence:** Outlawed local credential storage in application databases. Delegated authentication exclusively to Keycloak. Enforced explicit Pydantic schema validation at the transport layer to block injection attacks, and derived data ownership from the validated JWT subject to neutralize IDOR vulnerabilities.
*   **Defense Line:** "We neutralize OWASP A01 (Broken Access Control) by deriving user identity strictly from the cryptographically verified RS256 token subject context, preventing malicious IDOR payload manipulation."

### 2.3 Testing & CI/CD Verification (NIST SSDF & OWASP SAMM)
*   **Standard Influence:** Built a multi-layered verification toolchain inside Jenkins. All code formatting, unit tests, static code security scans (Bandit/Semgrep), and container dependency CVE audits (Trivy) must pass before a deployment is triggered.
*   **Defense Line:** "We implement shift-left security by integrating Trivy image scans directly into our pipeline. High or Critical CVEs act as a quality gate, failing the build before manifests are applied to the cluster."

### 2.4 Deployment & Policy as Code (CIS Controls & COBIT 2019)
*   **Standard Influence:** Manifests are evaluated dynamically using Open Policy Agent (OPA).
*   **Defense Line:** "We enforce OPA policies (`security.rego`) statically during the deployment phase to block dangerous misconfigurations—such as privileged containers or root-execution pods—satisfying CIS Control 16."

### 2.5 Monitoring & Incident Governance (ITIL 4 & CSF 2.0)
*   **Standard Influence:** Centralized log harvesting (Loki) and metric collection (Prometheus).
*   **Defense Line:** "We support ITIL 4 event management. If a service undergoes rollout failure, Jenkins automatically catches the crash loop and executes a safe, non-destructive rollout rollback to restore the system instantly, preserving high availability."
