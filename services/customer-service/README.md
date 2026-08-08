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
- `KEYCLOAK_ADMIN_URL` and `KEYCLOAK_ACTIVITY_REALM` for the internal Admin API; and
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

## Current boundary

Profile, address, account-status, service-side JWT validation/RBAC, ownership enforcement, domain-audit behavior, and normalized domain-plus-Keycloak activity retrieval are implemented. React integration, API-gateway routing, deployment manifests for this workload, Keycloak-to-profile lifecycle automation, durable event export, production rate limiting, and end-to-end browser journeys remain planned. This capability is PoC-scoped and is not a claim of production availability.
