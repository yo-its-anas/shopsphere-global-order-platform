# ShopSphere Global Order Platform

ShopSphere is a highly secure, observable, and event-driven Global Enterprise Order Management Platform designed as an EduQual Level 6 enterprise capstone. It demonstrates cutting-edge secure software engineering, Site Reliability Engineering (SRE), and DevSecOps compliance practices.

---

## 1. The Business Problem & Solution Objective

### 1.1 The Business Problem
Global e-commerce enterprises operate in highly volatile, concurrent, and high-threat environments. Standard monolithic platforms suffer from:
1.  **Transactional Write Collisions:** Race conditions during high-volume sales lead to stock overselling and corrupted shopping carts.
2.  **Lack of Bounded Contexts:** Tight database coupling between catalog search, profile indexing, and payment checkouts causes cascade system failures if a single database crashes.
3.  **No Security or Compliance Audit Trails:** Missing tamper-proof audits for administrative actions and lack of File Integrity Monitoring (FIM) exposes platforms to silent insider threats and credentials hijacking.

### 1.2 The Solution Objective
ShopSphere resolves these challenges by introducing a **decoupled, event-driven, least-privilege microservices architecture**:
*   **Decoupled Contexts:** Independent databases (Customer, Catalogue, Order) are managed exclusively by their owner microservices, communicated only via secure REST APIs and Apache Kafka event streams.
*   **Stock Safety (Synchronous Saga):** High-volume checkouts are protected via transactional database locks (`SELECT FOR UPDATE`) during inventory reservations, ensuring a $100\%$ zero-overselling guarantee.
*   **Central Observability & Compliance SIEM:** Aggregates real-time Prometheus metrics, Loki log streams, and container-level Wazuh SIEM alerts to grant complete operational, business, and security visibility.

---

## 2. Technical Architecture & Tech Stack

ShopSphere utilizes a modular, multi-tier tech stack hosted inside a virtualized single-node `kind` Kubernetes cluster:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        REACT SPA (Vite Frontend)                       │
│  - Ports: 5173 (Development Server), 80/443 (Production Ingress)       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI TRANSPORT API GATEWAY                     │
│  - Ports: 8000 (Central Ingress Endpoint)                              │
│  - Functions: JWT Validation, Correlation ID, Traceparent Propagation │
└──────────────────┬───────────────┬───────────────┬─────────────────────┘
                   │               │               │
                   ▼               ▼               ▼
┌────────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│  customer-service  │   │ catalogue-service │   │   order-service   │
│  - Port: 8000      │   │ - Port: 8000      │   │ - Port: 8000      │
│  - DB: customer_db │   │ - DB: catalogue_db│   │ - DB: order_db    │
└─────────┬──────────┘   └─────────┬─────────┘   └─────────┬─────────┘
          │                        │                       │
          └─────────────────┬──────┴───────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                SHARED POSTGRESQL & KAFKA DATA TIERS                   │
│  - PostgreSQL: Shared instance, separate logical databases            │
│  - Redis: High-performance Catalogue cache-aside                       │
│  - Kafka: High-speed KRaft event broker (outbox publisher)             │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Technology Stack
*   **Applications:** Python 3.10+ (FastAPI, SQLAlchemy 2.0, Alembic, Pydantic), React 19 (TypeScript, Vite).
*   **Identity & State:** Keycloak (OIDC Authentication), PostgreSQL, Redis Cache, Apache Kafka (KRaft mode).
*   **Observability & Security:** OpenTelemetry Collector, Prometheus, Grafana, Loki & Promtail, Open Policy Agent (OPA), Wazuh SIEM.
*   **CI/CD & DevSecOps:** Jenkins (23-stage declarative pipeline), Black, Ruff, Bandit, Semgrep, Trivy.

---

## 3. Repository Structure

```
/opt/shopsphere/shopsphere-global-order-platform/
├── docs/                        # Global documentation index
│   ├── adr/                     # Architectural Decision Records (ADRs 001-012)
│   ├── architecture/            # Domain designs, logging, & system maps
│   ├── assessment/              # Capstone compliance and audit sheets
│   ├── evidence/                # SRE validation, test, and security logs
│   ├── guides/                  # Operating manuals and deployment runbooks
│   └── standards/               # ISO, NIST, OWASP standards alignment matrix
├── frontend/                    # React / TypeScript Vite single-page app
├── platform/                    # Infrastructure deployment blueprints
│   ├── jenkins/                 # Pipeline setup and runbooks
│   ├── kind/                    # Cluster configuration and image-loading
│   ├── kubernetes/              # Base and overlays environment manifests
│   └── security/                # OPA security rego rules and exceptions
├── scripts/                     # Automated port-forwards, testing, & CLI tools
├── services/                    # Independently buildable FastAPI microservices
├── tests/                       # Global end-to-end and performance test suites
└── Jenkinsfile                  # Declarative CI/CD pipeline definition
```

---

## 4. Master Documentation Index

All platform operating guides, architecture designs, and quality audit logs are version-controlled and fully accessible:

### 4.1 Operating Guides & Manuals
*   📖 [Installation Guide](docs/guides/installation.md) — Reproducible host and development environment configuration.
*   📖 [Deployment Guide](docs/guides/deployment.md) — Jenkins CI/CD rollout workflows and manual bootstrap steps.
*   📖 [User Guide](docs/guides/customer-self-service.md) — End-to-end customer landing, profile, cart, and checkout workflows.
*   📖 [Administrator Guide](docs/guides/order-processing-administration.md) — Managing Keycloak, auditing database outboxes, and dashboard diagnostics.
*   📖 [Backup & Recovery Guide](docs/guides/backup-and-recovery.md) — Secure disaster-recovery and backup routines.
*   📖 [Troubleshooting Guide](docs/guides/troubleshooting.md) — Remediation steps for common cluster and application failures.

### 4.2 Structural Architecture Maps
*   🖼️ [System Architecture Maps](docs/architecture/system-architecture-maps.md) — Enterprise Software, High-Level Solution, Detailed System, and API Gateway diagrams.
*   🖼️ [Network & Data Flows](docs/architecture/network-and-data-flows.md) — Private Network maps, Level 0 & Level 1 DFDs, and UML Class diagrams.
*   🖼️ [Workflows & ERDs](docs/architecture/workflows-pipelines-and-database.md) — Checkout Sequence, Jenkins DevSecOps, and database relational ERD.
*   🖼️ [Recommended Production Architecture](docs/architecture/production/recommended-enterprise-architecture.md) — Global scale, high-availability GKE, and multi-zone replication schemas.

### 4.3 Quality, Standards & Compliance Audit Reports
*   ✅ [Capstone Compliance Audit](docs/assessment/compliance-audit.md) — Full requirements verification matrix.
*   ✅ [International Standards Alignment](docs/standards/international-standards-alignment.md) — Mapped alignment with ISO 12207, ISO 27001, NIST SSDF, OWASP Top 10, COBIT, and ITIL 4.
*   ✅ [SRE Observability Validation Report](docs/evidence/formal-validation-report.md) — Metrics scraping, Loki log ingest, and failure alert testing log evidence.
*   ✅ [Performance Baseline Report](tests/performance/performance_report.md) — Concurrent transaction latency percentiles ($p_{50}, p_{95}, p_{99}$).

---

## 5. Single-Node PoC Limitations & Production Recommendations

This platform runs as a **single-node Proof-of-Concept (PoC)** inside a single virtualized Google Cloud VM. It is an educational sandbox and does not support VM-level high availability, redundant disk storage, or cross-zone active replication natively.

To migrate ShopSphere Global safely to support millions of concurrent enterprise users, SREs must transition the platform to a fully distributed, multi-zone GCP environment utilizing **GKE, Cloud SQL HA, Cloud Memorystore, Cloud Armor WAF, and externalized SaaS observability (Datadog)** as documented in the [Recommended Production Architecture Manual](docs/architecture/production/production-architecture.md) and [Scaling for Millions Strategy](docs/architecture/production/scaling-for-millions.md).
