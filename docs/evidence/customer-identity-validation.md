# Customer Identity Validation Record

This record captures the non-sensitive results used by the Customer Identity and Account Management documentation review. It contains no credentials, tokens, customer data, external IP addresses, or secret values.

## Successful validation

| Boundary | Command | Result |
| --- | --- | --- |
| Kubernetes topology | `kubectl --context kind-shopsphere-poc get nodes` | Exactly one kind control-plane node reported Ready. |
| Workloads and exposure | `kubectl --context kind-shopsphere-poc get deployments,statefulsets,pods,services -A` | PostgreSQL, Keycloak, and customer-service workloads reported Ready; their application services were ClusterIP-only. API Gateway and frontend deployments were absent. |
| PostgreSQL | `make postgresql-status` | StatefulSet Ready; PVC Bound; `customer_db`, `keycloak_db`, and the catalogue persistence foundation `catalogue_db` exist with distinct owners; no credential values displayed. |
| Keycloak | `make keycloak-status` | Deployment Ready; PostgreSQL connection active; registration, roles, default customer role, password/brute-force/refresh/event settings, public frontend client, S256 PKCE, API audience, and authentication events validated. Activity reader had `view-events` without `manage-events` or `realm-admin`. |
| customer-service | `make customer-service-status` | Deployment and pod Ready; liveness/readiness returned HTTP 200; Service ClusterIP-only. |
| Static manifests | `make validate-kubernetes`, `make validate-postgresql`, `make validate-keycloak`, `make validate-customer-service` | Rendering and non-destructive validation passed. |
| Frontend | `npm run format:check`, `npm run lint`, `npm test`, `npm run build` | Formatting and lint passed; 7 test files and 11 tests passed; production build succeeded. |

## Unresolved functional evidence

- Customer-service collected 25 tests, but execution did not complete during the review. No passing JUnit report was produced.
- `test-results/integration/customer-identity.xml` records 7 collected and 7 skipped live integration tests because the explicit integration environment was not enabled.
- API Gateway test definitions were inspected but were not executed during this review.
- No browser → Keycloak → API Gateway → customer-service journey was executed.
- No SMTP password-recovery, verified-email, MFA, failover, restore, or disaster-recovery journey was executed.

These limitations prevent any claim that the customer capability is complete or production-ready. Re-run the enforcing customer-service and live integration suites and retain their JUnit results before promoting the corresponding traceability statuses.
