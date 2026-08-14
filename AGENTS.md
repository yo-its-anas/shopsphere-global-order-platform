# ShopSphere Engineering Context

This file is the primary handoff context for AI coding agents and engineers working in
this repository. Read it before changing code, infrastructure, tests, or documentation.
Repository evidence is authoritative when this summary and the implementation differ.

## Project identity

ShopSphere Global Enterprise Order Management Platform is an EduQual Level 6 enterprise
capstone implemented as a professional monorepo. It demonstrates modular services,
identity, transactional persistence, caching, asynchronous events, Kubernetes platform
engineering, CI validation, observability, and security-oriented engineering.

Do not organize filenames, documentation, application metadata, labels, images, scripts,
diagrams, or technical concepts around internal implementation timing. Use professional
capability-oriented terminology.

## Repository map

- `services/customer-service` — customer profiles, addresses, account metadata, domain
  audit history, and safe activity presentation.
- `services/catalogue-service` — product catalogue, categories, pricing, inventory,
  reservations, inventory movements, Redis cache-aside behavior, and Kafka outbox
  production.
- `services/order-service` — customer carts, checkout Saga orchestration, immutable order
  snapshots, order history, controlled lifecycle, audit records, and Kafka outbox.
- `services/analytics-service` — read-only Executive Business Operations aggregation.
- `services/api-gateway` — transport-only external API façade. It must not contain domain
  business logic.
- `frontend` — React, TypeScript, and Vite application using the API Gateway for business
  traffic and Keycloak for OIDC authentication.
- `shared` — stable conventions and genuinely reusable cross-service assets; never a
  dumping ground for domain logic.
- `infrastructure/terraform` — validation- and import-oriented GCP PoC baseline. The VM
  already exists; never assume it is safe to recreate it.
- `platform/kind` — single-control-plane `shopsphere-poc` kind cluster configuration and
  lifecycle scripts.
- `platform/kubernetes` — Kustomize base and PoC/production-reference overlays.
- `platform/jenkins` and root `Jenkinsfile` — CI validation without production deployment.
- `platform/monitoring` — monitoring architecture boundary; Prometheus/Grafana/Loki/OTel
  workloads are not yet deployed merely because application metrics exist.
- `platform/security` — security tooling and policy boundary.
- `tests` — cross-service integration, end-to-end, performance, and supporting evidence.
- `docs` — architecture, ADRs, APIs, guides, standards, viva material, and evidence.
- `scripts` — safe, idempotent diagnostics and validation utilities.

## PoC topology and limitations

The implemented PoC runs on one Ubuntu 22.04 Google Cloud VM with approximately 32 GB
RAM and one single-node kind Kubernetes cluster. Multiple replicas on this topology do
not provide host-level high availability.

Namespaces:

- `shopsphere-apps`
- `shopsphere-data`
- `shopsphere-platform`
- `shopsphere-monitoring`
- `shopsphere-security`

PostgreSQL, Redis, Kafka, Keycloak, and application services use internal Kubernetes
Services. PostgreSQL, Redis, Kafka, Jenkins, and the Keycloak administration interface
must not be publicly exposed. Existing NetworkPolicies express intent, but enforcement
depends on a compatible CNI.

The logical PostgreSQL databases currently include:

- `customer_db`
- `catalogue_db`
- `order_db`
- `keycloak_db`

They share one PostgreSQL server and persistent volume as a PoC resource optimization.
This is logical separation, not infrastructure isolation or HA. Never recreate the
PostgreSQL PVC or destroy existing data as part of ordinary development.

Redis is a performance optimization only. PostgreSQL remains authoritative for products,
prices, inventory, customers, carts, and orders. Kafka is a single-broker KRaft PoC and
must not be described as highly available.

## Identity and security boundaries

Keycloak is the sole identity and credential authority. It owns registration,
authentication, passwords, password policy, login/logout, token issuance, roles, and
authentication events. Customer-service never stores passwords or tokens.

Realm: `shopsphere`

Principal roles:

- `customer`
- `support`
- `operations_admin`
- internal service roles where explicitly configured, such as `order_service`

The React frontend uses Authorization Code Flow with PKCE and contains no client secret.
Frontend role checks are user-experience controls only. Every service must validate JWT
signature, issuer, audience, expiry, and roles server-side. Ownership must derive from
the immutable Keycloak `sub` claim; email is not an immutable identity key.

Never log, persist in telemetry, commit, or expose:

- passwords or password hashes;
- bearer or refresh tokens;
- client secrets or administrative credentials;
- database URLs containing credentials;
- Kubernetes Secret values;
- real customer information.

Prevent IDOR by resolving the authenticated subject at the service boundary rather than
trusting customer identifiers supplied by a browser. Support access is primarily
read-only. Administrative mutation rights must remain explicit and least-privileged.

## Service conventions

All FastAPI services follow these conventions:

- application factory plus module-level ASGI entry point;
- versioned business APIs below `/api/v1`;
- `GET /health/live`, `GET /health/ready`, and `GET /api/v1/info`;
- internal Prometheus text exposition at `GET /metrics`;
- typed configuration sourced from environment variables;
- structured JSON logs with UTC timestamps and correlation IDs;
- validated or generated `X-Request-ID` returned to the caller;
- centralized safe error responses;
- Pydantic request/response models; never expose ORM records directly;
- UUID domain identifiers and timezone-aware UTC application timestamps;
- independently installable and container-buildable services;
- numeric non-root container runtime.

Prometheus metric labels must be bounded. Never use customer, user, order, cart,
product, reservation, email, JWT subject, correlation ID, token, raw query, or raw path
values as labels. HTTP metrics use framework route templates and status classes.
`/metrics` must remain internal and excluded from public ingress.

## Implemented business capabilities

### Customer Identity and Account Management

- Keycloak self-registration and OIDC authentication architecture.
- Idempotent customer-profile provisioning keyed by immutable Keycloak subject.
- Own-profile retrieval and allowed-field updates.
- Address create/list/update/delete/default selection.
- Customer-domain append-only audit events.
- Safe normalized customer activity combining domain audit and Keycloak identity events.
- Support/operations views and explicit administrative account-status controls.
- API Gateway customer routing and Kubernetes deployment.

Known validation issue: three customer-service activity tests currently expose an
existing SQLite test-path defect when timezone-naive persisted audit timestamps are
sorted with timezone-aware Keycloak timestamps. The error is:
`TypeError: can't compare offset-naive and offset-aware datetimes`. Do not misreport the
full customer suite as passing until this is corrected and revalidated.

### Product Catalogue and Inventory Management

- Categories, products, lifecycle, PostgreSQL search/filter/pagination, and Decimal
  currency-aware pricing.
- Inventory balances with derived availability and invariant enforcement.
- Append-only inventory movements and calculated inventory statistics.
- Atomic, idempotent inventory reservation/release/consumption with concurrency control.
- Cache-aside Redis reads with TTL, invalidation, malformed-data handling, and
  PostgreSQL fallback.
- Transactional PostgreSQL outbox and asynchronous Kafka publisher using versioned
  event envelopes.
- API Gateway routes, frontend workflows, Kubernetes deployment, tests, and evidence.

Do not directly edit `quantity_available`; it is derived as
`quantity_on_hand - quantity_reserved`. Stock and reservation quantities may not be
negative, and reserved stock may not exceed on-hand stock.

### Enterprise Order Processing

- Subject-owned active shopping carts and cart items.
- Server-authoritative product, price, and availability validation.
- Decimal order calculations and immutable `OrderItem` commercial snapshots.
- Idempotent checkout using a caller-stable `Idempotency-Key`.
- Reservation-based Saga workflow with compensation and reconciliation evidence.
- Orders, status history, audit history, customer history/detail, support/admin views,
  cancellation, and controlled lifecycle transitions.
- Transactional outbox events following the existing catalogue event architecture.
- API Gateway routing, frontend workflows, Kubernetes deployment, tests, and evidence.

Never trust prices, totals, availability, customer IDs, or order ownership supplied by
the frontend. Order-service must use catalogue-service APIs and must never query or
modify `catalogue_db` directly.

### Executive Business Operations Analytics

Analytics-service is a read-only aggregation layer. It queries existing owner APIs and
does not query their databases or become authoritative for customer, product, inventory,
price, or order state.

Implemented endpoints:

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/orders`
- `GET /api/v1/dashboard/inventory`
- `GET /api/v1/dashboard/customers`
- `GET /api/v1/dashboard/operations`
- `GET /api/v1/dashboard/alerts`

Operations administrators can access executive summary/order metrics. Support and
operations administrators can access selected customer, inventory, operations, and
alert views. Ordinary customers cannot access global executive metrics.

Simulated revenue includes `CONFIRMED`, `PROCESSING`, and `FULFILLED` order totals and
excludes `PENDING`, `CANCELLED`, and `FAILED`. Revenue remains separated by currency;
never invent exchange rates. Dependency failure produces explicit `partial` or
`unavailable` metadata and `null` fields, not fabricated zeros.

## Messaging conventions

Catalogue-service and order-service use a transactional outbox. Domain mutation and
outbox insertion commit atomically. Kafka publication is asynchronous and retryable;
Kafka failure must not corrupt committed business state.

Delivery is at least once. Duplicate delivery is possible, so future consumers must be
idempotent by `event_id`. The common event envelope includes:

- `event_id`
- `event_type`
- `event_version`
- `aggregate_type`
- `aggregate_id`
- `occurred_at`
- `correlation_id`
- `producer`
- safe `payload`

Events must not contain credentials, JWTs, passwords, or unnecessary PII.

## Observability state

All five FastAPI workloads expose common HTTP/process/service Prometheus metrics.
Additional bounded metrics cover:

- Gateway upstream requests, failures, status classes, and latency;
- Order checkout attempts/results and lifecycle transitions;
- Catalogue reservation attempts/results, cache hits/misses, and outbox publication;
- Analytics aggregation/dependency outcomes, including partial aggregation.

Prometheus, Grafana, Loki, an OpenTelemetry Collector, a trace backend, and Wazuh are not
deployed by application instrumentation. Follow
`docs/architecture/observability-architecture.md` and `platform/monitoring/README.md`.

## Frontend boundaries

The frontend uses React, TypeScript, Vite, React Router, Vitest, Testing Library, ESLint,
and Prettier. It preserves a feature-based structure under `src/` and uses centralized
authentication and API abstractions.

All business calls go through API Gateway. Do not call customer-service,
catalogue-service, order-service, or analytics-service directly from React. Do not
decode a token and treat client-side claims as authoritative security decisions. Do not
log tokens or persist them as debug data. Unrelated dashboard areas may retain clearly
labelled demonstration data until real APIs exist; implemented capabilities should use
their real Gateway APIs.

## Infrastructure safety

- Never run `terraform apply` unless the user explicitly requests and authorizes it.
- The existing VM may be imported into Terraform state; do not recreate or destroy it.
- Never generate service-account keys.
- Never commit Terraform state, plan files, passwords, generated Kubernetes Secrets, or
  actual environment files.
- Use `ClusterIP` for internal services. Do not add NodePort or LoadBalancer exposure for
  PostgreSQL, Redis, Kafka, internal FastAPI services, Jenkins, or Keycloak admin.
- Cluster deletion and other destructive scripts must require explicit confirmation.
- Preserve existing persistent volumes and user data.
- Do not claim the PoC is production HA.

Production evolution targets GKE across nodes/zones, managed HA PostgreSQL, replicated
or managed Redis, replicated/managed Kafka, autoscaling, resilient reconciliation
workers, stronger service identity/mTLS, durable telemetry storage, centralized SIEM,
and tested disaster recovery.

## Change discipline

1. Inspect the relevant implementation, ADRs, tests, Kubernetes resources, and
   requirements traceability before editing.
2. Preserve user changes and unrelated dirty-worktree content.
3. Use existing architecture and naming patterns rather than introducing a second
   pattern for authentication, events, errors, caching, testing, or deployments.
4. Keep Gateway behavior transport-only and domain authorization authoritative in the
   owning backend.
5. Make migrations additive and reversible where practical. Never edit another
   service's schema.
6. Keep documentation evidence-based. A skipped, unexecuted, or environment-dependent
   test is not a pass.
7. Do not mark functionality complete unless code and validation evidence support it.
8. Do not alter Git history or historical branch names.
9. Use safe, non-destructive commands and never print secret values.

## Validation commands

Run checks from the repository root unless a command changes directory explicitly.
Use each service's existing `.venv` when present.

```bash
make help
make lint
make test
make validate
```

Per FastAPI service:

```bash
cd services/<service>
.venv/bin/black --check app tests
.venv/bin/ruff check app tests
.venv/bin/bandit -q -r app
.venv/bin/pytest
docker build -t shopsphere/<service>:local .
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm test -- --run
npm run build
```

Infrastructure and platform validation must remain non-destructive:

```bash
terraform -chdir=infrastructure/terraform fmt -check -recursive
terraform -chdir=infrastructure/terraform init -backend=false
terraform -chdir=infrastructure/terraform validate
kubectl kustomize platform/kubernetes/overlays/poc >/dev/null
```

Integration and end-to-end suites require explicit environment opt-in and test-safe
configuration. Never convert skipped integration tests into passes. Consult the relevant
guide under `docs/guides` or `tests/integration` before running live-cluster tests.

## Documentation authorities

Start with:

- `README.md`
- `docs/requirements-traceability.md`
- `docs/architecture/`
- `docs/adr/`
- `docs/api/`
- `docs/guides/`
- each service's `README.md`
- `platform/kind/README.md`
- `platform/kubernetes/README.md` where present
- `platform/monitoring/README.md`
- `platform/security/README.md`
- `platform/jenkins/README.md`

When recording evidence, distinguish among Implemented, Unit Validated, Integration
Validated, Platform Validated, End-to-End Validated, and Pending / Not Verified.
