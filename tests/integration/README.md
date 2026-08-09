# Customer Capability Integration Tests

This suite validates the implemented Customer Identity and Account Management path across Keycloak, API Gateway, customer-service, and PostgreSQL-backed readiness behavior. It does not test catalogue, order, analytics, Redis, or Kafka capabilities.

## Coverage

The live tests cover:

- Keycloak OIDC discovery and realm reachability;
- confirmation that customer self-registration is enabled;
- temporary simulated customer creation and authentication;
- access-token acquisition through a dedicated test-only Direct Access Grant client;
- idempotent customer profile provisioning;
- own-profile retrieval and update;
- address creation, listing, modification, and deletion;
- normalized activity and append-only audit history;
- customer, support, and operations-administrator role boundaries;
- unauthenticated, malformed-token, and genuinely expired-token rejection;
- address-ownership and administrative cross-customer IDOR attempts;
- optional readiness verification against an isolated customer-service instance with an intentionally unavailable test database.

Browser self-registration is not automated here because Keycloak intentionally exposes it as an interactive browser flow rather than a stable user-registration API. The suite verifies `registrationAllowed=true`, creates equivalent temporary simulated identities through a least-privilege test service account, then exercises real user authentication. Authorization Code with PKCE remains covered by frontend tests; interactive registration belongs in a browser end-to-end suite.

## Safety boundary

Live execution is disabled unless both of these values are explicitly set:

```bash
SHOPSPHERE_RUN_CUSTOMER_INTEGRATION=true
SHOPSPHERE_TEST_ALLOW_IDENTITY_MUTATION=true
```

`SHOPSPHERE_TEST_ENVIRONMENT` must be `test`, `integration`, or `poc`. The suite refuses other values. Endpoints must be supplied explicitly and cannot contain embedded credentials.

All generated users have randomized `shopsphere-it-*` identities and `@example.invalid` email addresses. Passwords are generated in memory and are never printed, logged, committed, placed in reports, or reused. Temporary Keycloak users and addresses are removed in fixture cleanup where possible.

Customer profiles and audit events are intentionally retained. The customer API exposes no profile deletion operation, audit events are append-only, and the suite will not bypass the database trigger or issue direct database deletes. Unique simulated identifiers make retained evidence distinguishable from any legitimate record.

Never point this suite at a production realm, bind bootstrap administrator credentials, or reuse the React public client for password-grant testing.

## Required Keycloak test clients

Create these only in the controlled PoC/integration realm through a reviewed administrator process:

1. A dedicated Direct Access Grant client, such as `shopsphere-integration-tests`:
   - Direct Access Grants enabled;
   - standard, implicit, and service-account flows disabled;
   - no production redirect URIs;
   - `profile`, `email`, and `roles` scopes;
   - an access-token audience containing `shopsphere-api`;
   - preferably a client-specific access-token lifespan of 2–5 seconds so expiration can be tested within the bounded CI wait;
   - public or confidential. If confidential, inject its secret only at execution time.

2. A dedicated confidential service account, such as `shopsphere-integration-test-manager`, with only the realm-management permissions needed to view the realm, create/delete temporary users, set their credentials, and map the three existing realm roles. It must not receive `realm-admin`, manage clients, read events, impersonate users, or manage the realm more broadly than required.

The test manager credential belongs in a protected Jenkins credential binding or an ephemeral shell environment. It must not be written to `.env` files, command history, JUnit output, or repository configuration.

The issuer returned by the test token endpoint must exactly match customer-service's configured `KEYCLOAK_ISSUER`, and the token must contain the `shopsphere-api` audience. The suite will fail rather than weaken issuer or audience validation.

## Environment contract

Use [customer-identity.env.example](customer-identity.env.example) only as a variable-name reference. Do not populate and commit it.

Required variables:

- `SHOPSPHERE_TEST_KEYCLOAK_URL`
- `SHOPSPHERE_TEST_GATEWAY_URL`, including `/api/v1`
- `SHOPSPHERE_TEST_REALM`
- `SHOPSPHERE_TEST_OIDC_CLIENT_ID`
- optional `SHOPSPHERE_TEST_OIDC_CLIENT_SECRET`
- `SHOPSPHERE_TEST_ADMIN_CLIENT_ID`
- `SHOPSPHERE_TEST_ADMIN_CLIENT_SECRET`
- both explicit safety opt-ins

For expiration testing, set `SHOPSPHERE_TEST_JWT_CLOCK_SKEW_SECONDS` to the deployed customer-service value. The test waits for the Keycloak `expires_in` period plus that skew. If the total exceeds `SHOPSPHERE_TEST_MAX_EXPIRY_WAIT_SECONDS`, only the expiration test is reported as skipped.

Database-failure behavior is tested only when `SHOPSPHERE_TEST_DATABASE_FAILURE_READINESS_URL` identifies an isolated instance already configured with a deliberately unreachable test database. The suite never scales, patches, stops, or reconfigures the live PostgreSQL workload. If the URL is absent, that single test is reported as skipped.

## Endpoint access

The services are internal by design. Use protected port-forwards or an equivalent private Jenkins agent path. For example, when both workloads exist:

```bash
kubectl --context kind-shopsphere-poc -n shopsphere-platform \
  port-forward service/keycloak 8081:8080

kubectl --context kind-shopsphere-poc -n shopsphere-apps \
  port-forward service/api-gateway 8000:8000
```

Port-forward processes must be managed outside the test command and stopped afterward. Do not expose Keycloak administration, customer-service, or PostgreSQL publicly. If API Gateway is not deployed, provide an independently reviewed local gateway process connected to the internal customer-service; the tests must still target the gateway URL rather than customer-service directly.

## Run locally

Install the already-pinned customer-service development dependencies into an isolated environment:

```bash
python3 -m venv .venv-integration
.venv-integration/bin/python -m pip install -e 'services/customer-service[dev]'
```

Export configuration through the current protected shell or secret manager, then run:

```bash
make customer-integration PYTHON=.venv-integration/bin/python
```

Or invoke Pytest directly:

```bash
mkdir -p test-results/integration
.venv-integration/bin/python -m pytest \
  -c tests/integration/pytest.ini \
  tests/integration/customer_identity \
  --junitxml=test-results/integration/customer-identity.xml
```

Without explicit live opt-in, collection succeeds and tests are safely skipped:

```bash
python3 -m pytest -c tests/integration/pytest.ini \
  tests/integration/customer_identity --collect-only
```

## Jenkins

The root Jenkinsfile contains a conditional `PoC customer integration tests` stage. It executes only when `SHOPSPHERE_RUN_CUSTOMER_INTEGRATION=true`; otherwise no identity or environment mutation occurs. Configure endpoints and non-secret values at job/folder level and inject both client credentials through masked Jenkins credentials.

JUnit XML is written to `test-results/integration/customer-identity.xml`, published by the existing report stage, and archived with the other machine-readable test evidence. Jenkins console output must never echo the integration environment or run with shell tracing.
