# Security Policy

Do not report vulnerabilities through public issues or commit credentials, tokens, private keys, or customer data. Until a private reporting channel is established, contact the project owner directly and provide the affected component, reproduction steps, impact, and suggested mitigation.

Security controls and tooling are introduced incrementally under `platform/security/`. This educational PoC is not approved for production data.

## Customer identity security boundary

Keycloak exclusively owns customer passwords, password policies, authentication, sessions, tokens, and identity events. Customer-service must never store or log passwords, password hashes, reset tokens, JWTs, refresh tokens, Keycloak administrator credentials, or confidential client secrets as customer data.

The current PoC runs Keycloak, PostgreSQL, customer-service, kind, and Docker on the same physical GCP VM. ClusterIP Services and Kubernetes controls reduce accidental exposure but do not create host-level high availability or independent security failure domains. NetworkPolicy enforcement depends on a compatible CNI, and local HTTP/tunnel access is not a production transport model.

Production requires separated and replicated identity and database infrastructure, private administration, TLS, external secret management and rotation, MFA, verified recovery, monitored abuse controls, regional database availability, automated backups and PITR, durable audit export, and tested incident recovery.
