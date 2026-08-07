# ADR-005: Use Keycloak for identity and RBAC

## Status

Proposed — configuration placeholders exist, but no realm, client, role, user, or deployed Keycloak evidence exists.

## Context

Customer and administrative journeys require centralized authentication and role-based authorization without building security-sensitive identity functionality inside domain services.

## Decision

Use Keycloak as the PoC OpenID Connect identity provider. Define clients and roles for user and administrative journeys, authenticate at the gateway, and require services to validate tokens and enforce authorization relevant to their resources.

## Alternatives considered

- Custom authentication: unacceptable security risk and unnecessary scope.
- Cloud Identity Platform: managed, but less portable and less suitable for a self-contained kind demonstration.
- Direct LDAP integration: enterprise-relevant but adds directory dependencies and does not itself provide the required application token flows.

## Consequences

Identity concerns are centralized and standards-based. Keycloak introduces operational state, configuration lifecycle, token-key rotation, and availability dependencies. RBAC still requires service-level policy design.

## Security implications

Use TLS, secure redirect URIs, short-lived tokens, protected administrative access, strong password and MFA policies where feasible, key rotation, audit logging, and least-privilege roles. Never store realm secrets in Git.

## PoC limitations

A single Keycloak instance would be a single point of failure. Federation, MFA, SMTP, hardened TLS, rotation automation, and enterprise lifecycle integration may be demonstrated only partially. None is implemented on Day 1.

## Production evolution

Use a supported highly available deployment or managed identity service, external database, enterprise federation, MFA, automated provisioning, secret rotation, backup, monitoring, and formally governed authorization.

## Viva defence notes

Differentiate authentication from authorization: Keycloak issues identity and role claims, while services remain responsible for resource-level decisions. Emphasize avoidance of bespoke identity code.
