# Architecture Decision Records

Architecture Decision Records (ADRs) capture significant choices, their context, alternatives, consequences, and evolution. An `Accepted` status means the decision governs the repository; it does not by itself prove that all related runtime capabilities have been implemented.

## Index

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-modular-microservices-architecture.md) | Modular microservices architecture | Accepted |
| [ADR-002](ADR-002-single-vm-kind-poc.md) | Single GCP VM and single-node kind for the PoC | Proposed |
| [ADR-003](ADR-003-separate-poc-and-production-architecture.md) | Separate PoC and recommended GKE production architecture | Accepted |
| [ADR-004](ADR-004-fastapi-versioned-rest-apis.md) | FastAPI REST APIs with `/api/v1` routes | Proposed |
| [ADR-005](ADR-005-keycloak-identity-rbac.md) | Keycloak for identity and RBAC | Accepted |
| [ADR-006](ADR-006-postgresql-redis-data-platform.md) | PostgreSQL for transactions and Redis for caching | Accepted |
| [ADR-007](ADR-007-kafka-domain-events.md) | Kafka for asynchronous domain events | Accepted |
| [ADR-008](ADR-008-monorepo-capstone.md) | Monorepo for the enterprise capstone | Accepted |
| [ADR-009](ADR-009-jenkins-cicd-devsecops.md) | Jenkins for CI/CD and DevSecOps orchestration | Proposed |
| [ADR-010](ADR-010-utc-timestamps-json-logs.md) | UTC timestamps and structured JSON logs | Accepted |
| [ADR-011](ADR-011-reservation-based-order-saga.md) | Reservation-based Saga for order checkout | Accepted and implemented for the PoC |
