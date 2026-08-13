# Tests

Contains capability-scoped unit, integration, end-to-end, and performance test areas. Live integration suites are opt-in and must use controlled dependencies, simulated data, and machine-readable results.

The implemented [Customer Identity and Account Management integration suite](integration/README.md) is limited to Keycloak, API Gateway, customer-service, and its PostgreSQL readiness boundary.

The explicitly enabled [Enterprise Order Processing E2E suite](end-to-end/order_processing/README.md)
uses simulated identities and data through the deployed API Gateway. It writes JUnit,
JSON and Markdown evidence, and it never converts a disabled or skipped run into a pass.

Provides cross-service test suites organized by scope. Service-local tests remain with their services; these suites validate platform and business flows across boundaries.
