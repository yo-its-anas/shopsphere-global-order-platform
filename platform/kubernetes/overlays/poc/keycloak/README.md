# Keycloak PoC Identity Provider

This overlay deploys one Keycloak instance into `shopsphere-platform` and connects it to `keycloak_db` through the internal `postgresql.shopsphere-data.svc.cluster.local` Service. It is designed for the single-node ShopSphere proof-of-concept and is **not production high availability**.

## Realm structure

The version-controlled, sanitized realm import creates the `shopsphere` realm with these realm roles:

- `customer` for customer self-service and the default registration role;
- `support` for explicitly governed support operations; and
- `operations_admin` for restricted operational administration.

These are identity roles, not a substitute for customer-service ownership checks. Backend services must validate token signature, issuer, audience, expiry, and relevant roles, then enforce resource ownership independently.

## Clients and token flow

`shopsphere-frontend` is a public OpenID Connect client. It enables only Authorization Code Flow, has no client secret, disables implicit and password grants, and uses the environment-specific `SHOPSPHERE_FRONTEND_BASE_URL` for redirects and browser origin checks. A realm client policy uses Keycloak's supported `pkce-enforcer` executor to require S256. The PoC overlay supplies `http://localhost:5173`; another environment must override it with its exact trusted origin.

`shopsphere-api` is a bearer-only resource-server audience. The frontend client adds this audience to access tokens so the API gateway and services can reject tokens issued for unrelated clients.

`shopsphere-service-integration` is a disabled-by-default-privilege confidential service account for future controlled machine integration. Keycloak generates its secret inside the realm database during import; no secret appears in Git. It has no application roles or broad scopes until a reviewed integration requires them.

`shopsphere-customer-activity-reader` is a separate confidential service account used only by customer-service's identity-activity adapter. Interactive and direct-access grants are disabled. `make keycloak-configure` grants only `realm-management/view-events`, reads the Keycloak-generated client credential without displaying it, and reconciles it into `shopsphere-apps/shopsphere-customer-activity-keycloak`. It does not receive `manage-events`, `view-users`, or `realm-admin`.

React initiates login with Authorization Code Flow and S256 PKCE, retains tokens in memory, sends the access token through the API gateway, refreshes only within the configured session, and uses the OpenID Connect logout endpoint. Frontend role checks affect presentation only; server authorization remains authoritative.

## Registration and passwords

Self-registration is enabled with email as the username, duplicate emails disabled, and usernames immutable. New accounts receive the `customer` role. Keycloak owns credentials, password hashing, password policy, recovery, brute-force protection, sessions, tokens, and authentication events. Customer-service must never receive or store passwords.

The password policy requires length, upper- and lower-case characters, a digit, a special character, and password history. Password reset is enabled, but email delivery is not configured in this PoC; recovery cannot be considered operational until SMTP is securely configured. Email verification is therefore not claimed as implemented.

## Sessions, events, and audit

Access tokens are short-lived, refresh-token rotation is enabled with reuse rejected, and session lifetimes are bounded. Selected user authentication events and administrative events are persisted in the Keycloak database for seven days; administrative representation details are disabled. Customer-service reads selected events through the dedicated activity reader and normalizes them without exposing IP addresses, sessions, tokens, credentials, administrator identities, or raw event details. Customer-domain audit history remains owned by customer-service as defined in ADR-005.

This pull-based PoC introduces an availability dependency on Keycloak and permits the customer-service workload to read retained realm events. The credential must be mounted only into customer-service, rotated when exposure is suspected, and protected with network policy and access monitoring. Production should prefer a durable, allow-listed identity-event export with privacy-governed retention rather than synchronous Admin API reads.

## Credentials and deployment

The committed Secret example contains placeholders only and is not rendered by Kustomize. Create the live namespace-scoped Secret using hidden prompts:

```bash
make keycloak-secret
```

For controlled automation, explicitly generate bootstrap values:

```bash
./scripts/create-keycloak-secret.sh --generate
```

The helper copies the existing Keycloak database password from the PostgreSQL Secret without displaying or decoding it. It creates new bootstrap administrator credentials directly in the Kubernetes API and preserves an existing Secret.

Validate and deploy:

```bash
make validate-keycloak
make keycloak-apply
kubectl --context kind-shopsphere-poc -n shopsphere-platform rollout status deployment/keycloak --timeout=420s
make keycloak-configure
make keycloak-status
```

For local administrative access, use an explicitly bound loopback port-forward. Do not bind to all interfaces:

```bash
kubectl --context kind-shopsphere-poc -n shopsphere-platform port-forward --address 127.0.0.1 service/keycloak 8080:8080
```

The Service is ClusterIP-only and no Ingress is created. A future ingress must publish required realm endpoints while denying public access to `/admin` and the management port. NetworkPolicy enforcement depends on the installed cluster network plugin.

Startup import creates the realm only when it does not already exist. Existing realm state is intentionally preserved on pod restart. `make keycloak-configure` idempotently reconciles the authoritative ShopSphere client-policy profile, policy, dedicated activity-reader client, least-privilege role, and runtime Kubernetes Secret after the realm exists. Other configuration changes for an established realm require a reviewed migration or controlled administrative automation; replacing live realm state automatically could delete users or credentials.

## PoC limitations and production evolution

One Keycloak pod, one PostgreSQL pod, one kind node, and one VM provide no host-level availability. The PoC also lacks production TLS termination, SMTP, verified email, MFA, federation, external secret management, automated key rotation, protected public ingress, immutable event export, and tested identity disaster recovery.

Production should use a supported highly available Keycloak topology or evaluated managed identity service, regional managed PostgreSQL, private administrative connectivity, TLS, phishing-resistant MFA, secure SMTP, verified registration, enterprise federation, external secret management, workload identity, signing-key rotation, durable event export, monitored authentication abuse, backups, recovery testing, and formally reviewed role governance.
