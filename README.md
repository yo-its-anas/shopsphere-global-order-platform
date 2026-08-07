# ShopSphere Global Enterprise Order Management Platform

ShopSphere is an EduQual Level 6 enterprise capstone that demonstrates the foundations of a secure, observable, event-driven global order management platform. This repository is a Day 1 monorepo scaffold: it defines ownership, delivery boundaries, and engineering conventions without implementing complete business features.

## Mandatory functional modules

1. **Customer Management** — customer profiles, addresses, and account-facing data.
2. **Catalogue Management** — products, pricing, availability, and catalogue queries.
3. **Order Management** — order capture, validation, lifecycle, and orchestration.
4. **Analytics and Reporting** — operational metrics, read models, and business insights.
5. **API Gateway and User Experience** — a controlled API entry point and React user interface, secured through Keycloak.

## Architecture scope

The **PoC architecture** targets one Ubuntu 22.04 Google Cloud VM. Docker hosts the development toolchain and a single-node kind Kubernetes cluster runs the application and supporting components. PostgreSQL, Redis, Kafka, and Keycloak are intentionally consolidated for demonstrability and cost control. This topology is not highly available.

The **production-reference architecture** documents the recommended evolution: managed or highly available data services, multi-node Kubernetes across failure domains, resilient Kafka, external secrets and identity integrations, independent scaling, protected ingress, backups and disaster recovery, and centralized security and observability. Production-reference assets are guidance, not PoC deployment promises.

## Technology stack

- Python, FastAPI, SQLAlchemy, Alembic, Pytest, Ruff, Black, and Bandit
- React and the Node.js ecosystem
- PostgreSQL, Redis, Apache Kafka, and Keycloak
- Docker, Kubernetes (kind), Terraform, and Jenkins
- Prometheus, Grafana, OpenTelemetry, and Loki
- Trivy, Semgrep, Wazuh, and Open Policy Agent (OPA)
- Markdown, Mermaid, PlantUML, and Draw.io

## Seven-day delivery approach

| Day | Outcome |
| --- | --- |
| 1 | Monorepo foundation, boundaries, standards, and evidence checklist |
| 2 | Service skeletons, shared contracts, database migration baseline, and frontend shell |
| 3 | Customer and catalogue vertical slices |
| 4 | Order workflow and Kafka event integration |
| 5 | Analytics, gateway integration, identity, and end-to-end flow |
| 6 | Kubernetes, CI/CD, observability, security controls, and test hardening |
| 7 | Validation, architecture documentation, evidence pack, and viva preparation |

Each day should produce reviewable evidence, automated checks, and updated architecture decisions. Scope is constrained to an educational PoC while production gaps remain explicit.

## Repository map

See the README in each major directory for its responsibility. Common entry points are `services/`, `frontend/`, `shared/`, `infrastructure/`, `platform/`, `tests/`, `docs/`, and `scripts/`.

## Getting started

Run `make help` to list safe foundation targets. Copy `.env.example` to a local ignored environment file only when configuration is introduced; never commit credentials.
