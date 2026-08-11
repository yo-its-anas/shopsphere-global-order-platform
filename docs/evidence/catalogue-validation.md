# Product Catalogue Validation Record

This record covers the implemented Product Catalogue and Inventory service boundary only. Order reservations, API Gateway catalogue/inventory routing, Kubernetes catalogue-service deployment, Redis, Kafka, and frontend integration remain outside this evidence.

## Automated results

| Boundary | Validation | Result |
| --- | --- | --- |
| Formatting | Ruff formatter check across `app`, `tests`, and `migrations` | Passed |
| Formatting | Black checked 43 Python files individually | Passed |
| Lint | Ruff | Passed |
| Security static analysis | Bandit over `app` | Passed |
| Service tests | Pytest with signed simulated JWTs and repository-isolated API/domain tests | 34 tests passed; 81% application coverage |
| Persistence contract | SQLAlchemy metadata tests | Passed; price precision, inventory balance/version constraints, idempotency uniqueness, and movement constraints are present |
| Alembic offline | Revision graph and PostgreSQL SQL generation | Passed; one head: `002_enterprise_inventory` |
| Alembic PostgreSQL round trip | Upgrade, five-table verification, constraint/trigger execution, downgrade, and re-upgrade against disposable PostgreSQL 16 | Passed |
| Alembic drift | `alembic check` after upgrade against disposable PostgreSQL 16 | Passed; no new upgrade operations detected |
| Container | `docker build --tag shopsphere/catalogue-service:poc services/catalogue-service` | Passed |

No live PoC schema migration or catalogue-service deployment was performed. Disposable PostgreSQL containers were bound to localhost, contained no real data or credentials, and were removed after validation.

## Covered behavior

- category create/update, normalized slug uniqueness, parent validation, and cycle rejection;
- product registration/update/deactivation and normalized immutable SKU uniqueness;
- active/searchable customer visibility and broader read-only support visibility;
- immediate effective decimal price replacement with retained history;
- supported-currency and invalid monetary-value rejection;
- customer/support write rejection and operations-administrator mutation access;
- text/SKU/category/status search, sorting, pagination, and invalid query validation;
- missing/invalid authentication, invalid UUIDs, mass-assignment rejection, OpenAPI paths, and database readiness failure response.
- stock initialization, receipt, damage, manual correction, and derived availability;
- non-negative/reserved-within-on-hand invariants and customer-safe availability;
- idempotent movement commands, stale concurrent-writer rejection, and append-only history;
- customer/support/operations authorization boundaries and inactive-product hiding;
- calculated in-stock/low-stock/out-of-stock and unit-total statistics;
- PostgreSQL rejection of movement update/delete and negative on-hand balances.

## Evidence limitations

API/domain tests use an in-memory implementation of the repository contract because the available aiosqlite driver blocks before executing SQL in this host environment. SQLAlchemy metadata and Alembic are validated separately, including a real PostgreSQL migration round trip, drift check, append-only-trigger execution, and balance-constraint execution. A deployed catalogue-service-to-`catalogue_db` integration test remains required before claiming live persistence behavior. Order reservation/release/fulfilment behavior is not implemented.
