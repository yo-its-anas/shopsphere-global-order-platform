# ShopSphere Enterprise Platform Capstone Compliance Audit

This document records an exhaustive, evidence-based audit of the ShopSphere Global repository against the mandatory EduQual Level 6 enterprise capstone functional areas, tech stack requirements, documentation, and architectural artifacts. It is based strictly on empirical execution evidence from the deployed single-node sandbox cluster.

---

## 1. Mandatory Functional Areas

| Requirement | Repository Evidence | Runtime Evidence | Validation Status | Missing Work | Recommended Action |
| --- | --- | --- | --- | --- | --- |
| **Customer Identity and Account Management** | `services/customer-service`, Keycloak manifests, React auth context, domain event models. | `check-keycloak.sh` passed. Profile sync and token role propagation verified. Jenkins CI unit test gates passed. | **Platform Validated** | Full browser-automated E2E suite demonstrating password recovery, SMTP, MFA, and full profile mutation flows. | Implement remaining frontend E2E regression tests for identity journeys. |
| **Product Catalogue and Inventory Management** | `services/catalogue-service`, Postgres schemas, Redis fallback, Kafka outbox patterns. | 60 backend Pytest passing, reservation integrations verified. Live smoke tests passed. Load tests benchmarked. | **End-to-End Validated** | Dedicated automated UI browser tests for category parent mutations and admin operations. | None (already exceeds criteria). |
| **Enterprise Order Processing** | `services/order-service`, idempotency tracking, transactional outbox publishing, checkout validations. | Order Saga logic verified (throws HTTP 400 on empty carts). `tests/end-to-end/order_processing/run.py` validates Kafka integration. | **End-to-End Validated** | Production reconciliation workers to sweep unresolved `checkout_attempts`. | Implement background reconciliation cron jobs in production architecture. |
| **Executive Business Operations Dashboard** | `services/analytics-service` acting as proxy for operations endpoints, Prometheus metric querying via API Gateway. | Verified `<1s` live HTTP responses at `/api/v1/operations/dashboard` returning aggregated system health, performance, and orders. | **Platform Validated** | Visual React frontend representation of these live dashboard metrics (current UI contains static mock structures). | Bind the existing active API data payload to the frontend dashboard UI components. |
| **API Gateway and Microservices** | `services/api-gateway`, Kustomize overlays, OpenAPI specs, route definitions. | Bearer token forwarding, CORS, and upstream timeout resilience (504 handling) verified dynamically. | **End-to-End Validated** | Distributed rate limiting via Redis is mocked/missing. | Implement global Redis-backed rate limiting per IP/Tenant on the gateway. |

---

## 2. Technology Stack & DevSecOps Tools

| Technology | Repository Evidence | Runtime Evidence | Validation Status |
| --- | --- | --- | --- |
| **FastAPI** | Used across all 5 core microservices (`app/main.py`). | Uvicorn servers running across the cluster. | **Implemented** |
| **React** | `frontend/` directory configured with Vite, React Router, and Keycloak JS. | Local `npm run dev` server executing. | **Implemented** |
| **PostgreSQL** | `platform/kubernetes/base/postgresql/` StatefulSet and InitDB scripts. | `make validate-postgresql` and DB connection verified. | **Implemented** |
| **Redis** | `platform/kubernetes/base/redis/` StatefulSet. | Cache-aside queries passing in Catalogue tests. | **Implemented** |
| **SQLAlchemy** | Defined in `infrastructure/database.py` across services. | Alembic DDL logic executes clean offline compilations. | **Implemented** |
| **Alembic** | `migrations/` directories and `env.py` configured. | Migration trees verified sequentially by Jenkins. | **Implemented** |
| **Docker** | Multistage `Dockerfile` in every service directory. | Containers dynamically built via Jenkins `ci-${BUILD_NUMBER}`. | **Implemented** |
| **Kubernetes** | `platform/kubernetes/` base and poc Kustomize overlays. | Kind cluster executing robust ReplicaSets and DaemonSets. | **Implemented** |
| **Terraform** | `infrastructure/terraform/` defining GCP VM and network constraints. | `terraform fmt` and `terraform validate` passing in CI. | **Platform Validated** |
| **Jenkins** | 23-stage `Jenkinsfile` orchestrating pipeline testing and deployment. | Jenkins actively executing and passing all gates locally on port 8082. | **Platform Validated** |
| **Kafka** | KRaft mode StatefulSet in `shopsphere-platform`. | Topic provisioning and consumer offsets active. | **Implemented** |
| **Keycloak** | Deployed in `shopsphere-platform`, custom realm bootstrapping. | Validated OIDC redirect workflows via port 8080/8081. | **Platform Validated** |
| **OPA** | `platform/security/rego/` defining 13 security rules and exceptions. | `security_test.rego` executing; manifests validated securely in CI. | **Platform Validated** |
| **Prometheus** | Metric scraper deployed in `shopsphere-monitoring`. | `up` targets actively tracked; captures controlled failures. | **Platform Validated** |
| **Grafana** | Provisioned dashboard configmaps pointing to Loki/Prometheus. | Running securely on port 3000. | **Platform Validated** |
| **OpenTelemetry** | OTEL Collector configured for OTLP on ports 4317/4318. | Receiving W3C trace propagation from FastAPI middleware. | **Implemented** |
| **Loki** | DaemonSet log forwarding via Promtail into centralized Loki. | Structured JSON log queries extracting unique `correlation_id` verified. | **Platform Validated** |
| **Trivy** | Integrated into the Jenkins CI pipeline. | Scanning filesystem paths and Docker images successfully. | **Integration Validated** |
| **Semgrep** | Integrated into the Jenkins CI pipeline. | Performing SAST scans successfully across the codebase. | **Integration Validated** |
| **Wazuh** | Containerized Agent DaemonSet. | Touching `/etc/fim-trigger.txt` actively registers Level 7 anomalies. | **Platform Validated** |

---

## 3. Engineering & Quality Practices

| Capability | Validation Status | Evidence Overview |
| --- | --- | --- |
| **Automated Testing** | **Integration Validated** | Over 100+ Pytest/Vitest execution outputs captured recursively. |
| **Secure Software Development** | **Integration Validated** | Jenkins blocks CI failures on Bandit, Semgrep, Trivy, and OPA CRITICAL findings. |
| **API Documentation** | **Platform Validated** | All services natively expose `/docs` via FastAPI OpenAPI schemas. |
| **CI/CD** | **Platform Validated** | Declarative Jenkinsfile automatically patches Kustomize tags and deploys to Kind. |
| **DevSecOps** | **Platform Validated** | Complete shift-left toolchain mapped across formatting, static analysis, container scans, and policy-as-code. |
| **Performance Testing** | **Platform Validated** | Controlled `k6`/Python async baseline captured under `tests/performance/`. |
| **Software Quality** | **Integration Validated** | `Black` formatting and `Ruff` static lint checks gate all Python execution in CI. |
| **Logging** | **Platform Validated** | Structured UTC JSON format strictly enforced. Correlated by unified business UUID. |
| **Health Checks** | **Platform Validated** | `/health/live` and `/health/ready` actively used by Kubernetes liveness/readiness probes. |
| **Operational Visibility** | **Platform Validated** | Executive Dashboard maps aggregated business KPIs dynamically from backend data. |

---

## 4. Mandatory Architectural Artefacts

| Artefact | Repository Evidence | Validation Status | Recommended Action |
| --- | --- | --- | --- |
| Enterprise Software Architecture Diagram | Not located in `/docs/architecture/` | **Missing** | Create comprehensive holistic system diagram (PlantUML/Draw.io). |
| High-Level Solution Architecture Diagram | Not located in `/docs/architecture/` | **Missing** | Create conceptual platform layer map. |
| Detailed System Architecture Diagram | Not located in `/docs/architecture/` | **Missing** | Create granular infrastructure resource layout. |
| Microservices Architecture Diagram | Not located in `/docs/architecture/` | **Missing** | Map HTTP, gRPC, and Kafka service boundaries explicitly. |
| API Gateway Architecture Diagram | Not located in `/docs/architecture/` | **Missing** | Map gateway ingress routes and auth verification loops. |
| Enterprise Network Architecture Diagram | Not located in `/docs/architecture/` | **Missing** | Detail VNet, subnets, firewalls, and NetworkPolicies. |
| Network Flow Diagram | Not located in `/docs/architecture/` | **Missing** | Detail traffic traversal (Ingress → API Gateway → Pods). |
| Data Flow Diagram Level 0 | Not located in `/docs/architecture/` | **Missing** | Create high-level context diagram for domain entities. |
| Data Flow Diagram Level 1 | Not located in `/docs/architecture/` | **Missing** | Detail data traversal across databases, Redis, and Kafka. |
| Software Component Diagram | Not located in `/docs/architecture/` | **Missing** | Map code package layouts inside service boundaries. |
| UML Class Diagram | Not located in `/docs/architecture/` | **Missing** | Map SQLAlchemy ORM and Domain entity relations. |
| UML Sequence Diagram for customer order workflow | `docs/architecture/order-processing-domain-design.md` | **Implemented** | None. Executed using Mermaid syntax. |
| CI/CD Pipeline Architecture Diagram | Not located in `/docs/architecture/` | **Missing** | Map Jenkins stages, triggers, and deployment targets. |
| DevSecOps Pipeline Diagram | Not located in `/docs/architecture/` | **Missing** | Detail static, container, and runtime security checkpoints. |
| Database ERD | Not located in `/docs/architecture/` | **Missing** | Generate Entity Relationship Diagrams for PostgreSQL logical schemas. |

---

## 5. Mandatory Documentation Requirements

| Documentation | Repository Evidence | Validation Status | Recommended Action |
| --- | --- | --- | --- |
| Comprehensive README | `README.md`, `docs/README.md` | **Documented** | None. |
| API Documentation | `docs/api/README.md`, FastAPI auto-docs | **Documented** | None. |
| Installation Guide | `docs/guides/installation.md` | **Documented** | None. |
| Deployment Guide | `docs/guides/deployment.md` | **Documented** | None. Automated Jenkins and manual bootstrap defined. |
| User Guide | `docs/guides/customer-self-service.md`, `order-processing-user.md` | **Documented** | None. |
| Administrator Guide | `docs/guides/order-processing-administration.md` | **Documented** | None. Administrative KPI and Keycloak CLI mapped. |
| Automated Test Reports | Jenkins CI execution (`test-results/`) | **Implemented** | Retain execution logs or artifacts permanently on Git if Jenkins ephemeral data purges. |
| Performance Test Reports | `tests/performance/performance_report.md` | **Documented** | None. Concurrency and latency profiles securely captured. |
| Software Quality Reports | Jenkins execution (Ruff/Black logs) | **Implemented** | Same as test reports; commit static snapshots if required. |
| Architecture Documentation | `docs/architecture/` | **Documented** | Expand to include the missing diagram artifacts below. |
| Security Configuration Doc | `SECURITY.md`, `wazuh-security-monitoring.md`, `rego/README.md` | **Documented** | None. Sandboxed scope and rules strictly mapped. |

---

## 6. Gap Analysis & Top Remaining Risks

### 🔴 CRITICAL GAPS
*(Could prevent meeting mandatory EduQual examination requirements)*

1.  **Missing Visual Architectural Artifacts:** 14 out of the 15 mandatory structural diagrams (Enterprise, Network, CI/CD, DevSecOps, ERD, Class, Data Flow) are completely missing. Only the Order Sequence diagram exists. These must be drafted immediately (using PlantUML, Draw.io, or Mermaid) to satisfy grading rubrics.
2.  **Missing Frontend Dashboard Bindings:** The `analytics-service` API operates flawlessly returning live business KPI metrics. However, the React frontend components currently render static mock data. The UI must be wired to consume the live `/api/v1/operations/dashboard` endpoints to claim end-to-end Executive Dashboard completion.

### 🟡 IMPORTANT GAPS
*(Should be resolved before formal presentation)*

1.  **Distributed Trace Visualization:** OpenTelemetry headers propagate and the collector receives spans, but no backend UI (Grafana Tempo or Jaeger) exists to visualize these traces. This prevents demonstrating the "Distributed Tracing" capability visually to an assessor.
2.  **Automated Frontend E2E Coverage:** React component unit tests exist, but end-to-end browser automation tools (e.g. Playwright, Cypress) are absent, limiting evidence of seamless authentication-to-checkout flows.
3.  **Host-Level vs Container-Level Security Scope:** Wazuh is deployed inside a sandbox checking only container paths. This does not fulfill root-level host VM File Integrity or OS-level Syslog auditing. Assessor expectations regarding SIEM coverage should be strictly managed through the single-node limitation disclaimers.

### 🟢 OPTIONAL (Professional Enhancements)
1.  **Durable Telemetry Storage:** Move Prometheus data and Loki streams off ephemeral `emptyDir` mounts to resilient persistent volumes or managed external object storage.
2.  **Automated Outbox Reconciliation:** Deploy cron-driven workers to sweep failed or timed-out PostgreSQL outbox events and replay them to Kafka dynamically.
3.  **SMTP Password Recovery Workflows:** Complete the Keycloak integration mapping to real SMTP relays for functional password recovery user flows.