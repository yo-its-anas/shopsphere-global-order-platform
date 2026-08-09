# Production Architecture

Documents the recommended scalable, resilient, secure, and operable future state. It must clearly distinguish recommendations from implemented evidence.

## Customer identity evolution

The production identity direction is governed by the production-evolution section of [ADR-005](../../adr/ADR-005-keycloak-identity-rbac.md). It retains the separation between identity credentials and customer-domain data while adding resilient identity hosting, stronger authentication, lifecycle automation, protected administration, durable audit handling, privacy controls, monitoring, recovery, and formally governed authorization. These are recommendations, not implemented evidence.

Unlike the PoC, production must not place the only identity provider and only transactional database on one physical host. Use a supported multi-instance Keycloak topology or evaluated managed identity service across independent failure domains. Store identity and customer data in separately governed, regional managed PostgreSQL services or equivalent isolated databases with replication, encrypted automated backups, point-in-time recovery, tested failover, and explicit recovery objectives.

Production also requires private administrative access, TLS throughout exposed paths, external secret management and rotation, phishing-resistant MFA, verified-email and recovery delivery, durable privacy-governed identity-event export, immutable domain-audit retention, rate limiting, abuse monitoring, capacity testing, and disaster-recovery exercises. Merely increasing replicas inside the single-node PoC would not satisfy these requirements.
