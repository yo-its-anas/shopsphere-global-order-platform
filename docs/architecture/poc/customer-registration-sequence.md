# Customer Registration and Profile Provisioning Sequence

This sequence refines [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md). Keycloak owns registration, credentials, authentication, sessions, and tokens. Customer-service owns the domain profile and provisions it from a verified identity without receiving a password or storing a token.

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant React as React SPA
    participant Keycloak as Keycloak<br/>identity authority
    participant Gateway as API Gateway
    participant Service as customer-service
    participant Database as customer_db

    Customer->>React: Choose registration
    React->>Keycloak: Authorization request with PKCE
    Keycloak->>Customer: Keycloak-hosted registration form
    Customer->>Keycloak: Identity details and credentials
    Keycloak->>Keycloak: Create identity and securely manage credentials
    Keycloak-->>React: Authorization code
    React->>Keycloak: Exchange code with PKCE verifier
    Keycloak-->>React: Signed access token
    React->>Gateway: PUT /api/v1/customers/me<br/>Bearer access token
    Gateway->>Service: Forward bearer token and correlation ID<br/>(gateway JWT enforcement not implemented)
    Service->>Keycloak: Obtain/cache realm JWKS when required
    Service->>Service: Validate RS256 signature, issuer,<br/>audience, expiry, subject, and customer role
    Service->>Database: INSERT profile keyed by unique Keycloak sub<br/>ON CONFLICT DO NOTHING
    alt Profile inserted by this request
        Service->>Database: Append profile.provisioned audit event
        Database-->>Service: New domain profile UUID
        Service-->>React: profile + provisioned=true
    else Profile already exists or another request won the race
        Service->>Database: Select existing profile by Keycloak sub
        Database-->>Service: Existing domain profile UUID
        Service-->>React: profile + provisioned=false
    end
```

## Implemented boundary

Keycloak self-registration and the realm/client security baseline are implemented in the PoC platform. Customer-service implements JWT validation, the idempotent `PUT /api/v1/customers/me` provisioning operation, database uniqueness on `identity_provider_subject`, concurrency-safe insert-or-read behavior, and a single transactional provisioning audit event.

React OIDC integration and API-gateway customer routing are implemented in source. PostgreSQL, Keycloak, customer-service, and API Gateway are deployed, but the frontend is not deployed in the PoC cluster. The retained integration JUnit report contains seven skips, and the customer-service test run did not complete during the current review. The complete browser-to-service sequence is therefore not claimed as executed or functionally validated.

The Keycloak `sub` claim is the immutable external identity reference. CustomerProfile retains its own UUID. Email is copied only when a profile is first created; a later email claim for the same `sub` neither creates another profile nor silently overwrites customer-managed domain data. Explicit synchronization or reconciliation policy is a future integration concern.

No credential, password, access token, refresh token, authorization code, or PKCE verifier is persisted by customer-service or written to its audit metadata.
