# Customer Service

Owns ShopSphere customer business profiles, postal addresses, account status, and append-only customer-domain audit history. Keycloak remains the exclusive authority for authentication, credentials, password policy, tokens, roles, login/logout, and authentication events. This service never accepts or stores passwords, password hashes, reset tokens, refresh tokens, or client secrets.

The service uses an asynchronous FastAPI and SQLAlchemy architecture with application use cases, persistence-independent domain models, repository contracts, private ORM records, PostgreSQL persistence, Alembic migrations, structured JSON logging, and correlation IDs. An immutable unique Keycloak `sub` reference links an identity to a profile; independent UUIDs remain the domain primary keys.

## API surface

Operational endpoints remain unauthenticated:

- `GET /health/live`
- `GET /health/ready` — returns `503` when the required database is unavailable
- `GET /api/v1/info`

Customer self-service requires the `customer` role and resolves ownership only from the verified token subject:

- `POST`, `GET`, and `PATCH /api/v1/customers/me`
- `PUT /api/v1/customers/me` — idempotently provision from verified Keycloak claims or return the existing profile
- `POST` and `GET /api/v1/customers/me/addresses`
- `PATCH` and `DELETE /api/v1/customers/me/addresses/{address_id}`
- `PUT /api/v1/customers/me/addresses/{address_id}/default`
- `GET /api/v1/customers/me/activity`
- `GET /api/v1/customers/me/audit-history`

Support and operations routes are under `/api/v1/admin/customers`. The `support` role can list and view profiles, normalized activity, and domain audit history but cannot modify accounts. The `operations_admin` role has the same read access and may change account status through `PATCH /api/v1/admin/customers/{customer_id}/status` using a governed reason code.

## Security model

Access tokens are accepted only as bearer tokens. The verifier fetches and caches Keycloak JWKS asynchronously, permits only RS256, and validates signature, issuer, API audience, expiry, and required claims. It extracts only the allow-listed `customer`, `support`, and `operations_admin` roles from the configured realm and resource client. Unknown keys trigger a bounded JWKS refresh for signing-key rotation.

Self-service paths do not accept customer IDs. Address queries combine the address ID with the profile resolved from `sub`, returning `404` for another customer's address. Response schemas do not expose ORM objects or the external identity reference. Validation errors omit supplied values so credentials accidentally sent to an unsupported field are not reflected.

After successful Keycloak authentication, clients call `PUT /api/v1/customers/me`. The first valid request seeds the profile from `given_name`, `family_name`, and `email`; database conflict handling and the unique subject constraint make retries and concurrent calls return the same profile. Later email claims for the same `sub` do not re-key, duplicate, or silently overwrite the domain profile.

Domain mutations and their audit events commit in one transaction. Audit metadata is server-created and allow-listed; it contains field names, status transitions, and governed reason codes rather than arbitrary request content. PostgreSQL migration enforcement rejects updates and deletes against audit rows.

`/activity` merges customer-domain events with selected real Keycloak user and identity-administration events through a source-neutral provider. Responses expose UTC time, stable category/action/source/result values, and allow-listed context only. Raw Keycloak payloads, IP addresses, session identifiers, tokens, credentials, administrator details, and client secrets are excluded. `/audit-history` exposes the independently owned customer-domain record. A Keycloak outage returns a safe `503` for the merged view without fabricating identity events.

## Configuration

Copy `.env.example` only as a reference and inject actual values through the runtime secret mechanism. Required deployed settings are:

- `DATABASE_URL` for `customer_db` using the `customer_app` credential;
- `KEYCLOAK_ISSUER` for the `shopsphere` realm;
- `KEYCLOAK_AUDIENCE=shopsphere-api`; and
- optionally `KEYCLOAK_JWKS_URL` when internal discovery differs from the issuer URL;
- `KEYCLOAK_ADMIN_URL`, `KEYCLOAK_TOKEN_URL`, and `KEYCLOAK_ACTIVITY_REALM` for private back-channel Admin API and service-token access; and
- `KEYCLOAK_ACTIVITY_CLIENT_ID` and `KEYCLOAK_ACTIVITY_CLIENT_SECRET`, injected from the dedicated namespace-scoped Kubernetes Secret.

The example contains placeholders only. Never commit a populated environment file.

## Development and validation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/black --check app tests migrations
.venv/bin/ruff check app tests migrations
.venv/bin/bandit -q -r app
.venv/bin/pytest
DATABASE_URL='postgresql+psycopg://...' .venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

Tests use SQLite by default and can use isolated PostgreSQL by setting `TEST_DATABASE_URL`. Alembic must run as a controlled deployment step before the service receives traffic; application startup does not mutate schemas automatically.

## Validation evidence

The following statements are supported by the current review:

- the Kubernetes Deployment is Ready, its liveness and readiness endpoints return HTTP 200, and its Service is ClusterIP-only;
- PostgreSQL is Ready with a Bound PVC and separate `customer_db` and `keycloak_db` databases;
- Keycloak is Ready, records events, and provides the activity reader only `view-events` access;
- profile, address, status, JWT/RBAC, ownership, audit, and normalized activity implementations and their automated test definitions exist; and
- React customer tests and the frontend production build pass.

The customer-service suite collects 25 tests, but test execution did not complete during this documentation review. The retained live integration JUnit report records seven skipped tests because explicit PoC integration configuration was not supplied. Therefore profile, address, audit, service-side RBAC, and merged-activity behavior are **implemented but not claimed as end-to-end verified**. Run the service suite and the opt-in integration suite successfully before using them as examination execution evidence.

## Security assumptions and limitations

- Keycloak is the only credential authority. Customer-service does not store or process passwords, password hashes, reset tokens, access tokens, or refresh tokens as domain data.
- JWT validation assumes the configured issuer, audience, JWKS endpoint, and bounded clock skew match the tokens issued to ShopSphere. Gateway bearer propagation does not replace service-side validation.
- The confidential activity-reader credential is a PoC trade-off. It is delivered through a Kubernetes Secret and is limited to `view-events`, but compromise of customer-service could expose retained identity-event data.
- NetworkPolicy expresses API Gateway-only ingress intent, but enforcement depends on the installed CNI. The current kind network must not be treated as a production security boundary.
- The PoC uses one customer-service replica, one Keycloak pod, and one PostgreSQL pod on one kind node on the same physical GCP VM. A VM, Docker, node, or disk failure can affect the entire identity capability; there is no host-level high availability.
- API Gateway and frontend source integrations exist, but neither workload is deployed in the current cluster. TLS ingress, SMTP recovery, verified email, MFA, production rate limiting, durable event export, reconciliation of orphaned identities, and end-to-end browser validation remain outstanding.

Production must separate and replicate identity and database infrastructure, use a supported highly available Keycloak topology or evaluated managed identity service, use regional managed PostgreSQL with automated backups and PITR, enforce private networking and TLS, externalize and rotate secrets, export audit events durably, and test failover and recovery.
