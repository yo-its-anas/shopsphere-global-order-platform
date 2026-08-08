# ShopSphere Global Enterprise Order Management Platform

ShopSphere is an EduQual Level 6 enterprise capstone that demonstrates the foundations of a secure, observable, event-driven global order management platform. This monorepo defines ownership, delivery boundaries, and engineering conventions while keeping incomplete business capabilities explicitly identified as planned work.

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

## Capability delivery model

| Capability | Intended outcome |
| --- | --- |
| Foundation | Monorepo boundaries, engineering standards, shared conventions, and evidence governance |
| Customer Identity | Customer account capabilities and governed identity integration |
| Catalogue & Inventory | Product catalogue, pricing, availability, and inventory capabilities |
| Order Processing | Order lifecycle, orchestration, persistence, and domain-event integration |
| Operations Dashboard | Executive operational views backed by governed application data |
| Platform Engineering | Kubernetes, infrastructure as code, CI/CD, observability, and security controls |
| Architecture & Validation | Architecture documentation, automated validation, evidence, and viva preparation |

Each capability should produce reviewable evidence, automated checks, and updated architecture decisions. Scope is constrained to an educational PoC while production gaps remain explicit.

## Repository map

See the README in each major directory for its responsibility. Common entry points are `services/`, `frontend/`, `shared/`, `infrastructure/`, `platform/`, `tests/`, `docs/`, and `scripts/`.

## Getting started

Run `make help` to list safe foundation targets. Copy `.env.example` to a local ignored environment file only when configuration is introduced; never commit credentials.
