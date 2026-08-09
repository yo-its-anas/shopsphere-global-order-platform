# Tests

Contains capability-scoped unit, integration, end-to-end, and performance test areas. Live integration suites are opt-in and must use controlled dependencies, simulated data, and machine-readable results.

The implemented [Customer Identity and Account Management integration suite](integration/README.md) is limited to Keycloak, API Gateway, customer-service, and its PostgreSQL readiness boundary.

Provides cross-service test suites organized by scope. Service-local tests remain with their services; these suites validate platform and business flows across boundaries.
