# Security Policy

Do not report vulnerabilities through public issues or commit credentials, tokens, private keys, or customer data. Until a private reporting channel is established, contact the project owner directly and provide the affected component, reproduction steps, impact, and suggested mitigation.

Security controls and tooling are introduced incrementally under `platform/security/`. This educational PoC is not approved for production data.

## Customer identity security boundary

Keycloak exclusively owns customer passwords, password policies, authentication, sessions, tokens, and identity events. Customer-service must never store or log passwords, password hashes, reset tokens, JWTs, refresh tokens, Keycloak administrator credentials, or confidential client secrets as customer data.

The current PoC runs Keycloak, PostgreSQL, customer-service, kind, and Docker on the same physical GCP VM. ClusterIP Services and Kubernetes controls reduce accidental exposure but do not create host-level high availability or independent security failure domains. NetworkPolicy enforcement depends on a compatible CNI, and local HTTP/tunnel access is not a production transport model.

Production requires separated and replicated identity and database infrastructure, private administration, TLS, external secret management and rotation, MFA, verified recovery, monitored abuse controls, regional database availability, automated backups and PITR, durable audit export, and tested incident recovery.

## Catalogue and inventory security boundary

PostgreSQL is authoritative for products, prices, stock balances, movements and outbox
state. Redis is a performance cache only and must never be used to authorize a mutation,
set a balance or make a reservation decision. Kafka transports asynchronous facts after
database commit; it is not an authorization or transaction authority. Catalogue-service
validates Keycloak JWT signature, issuer, audience, expiry and allow-listed roles even
when API Gateway forwards the request.

Customers are read-only and see only governed active catalogue data and safe
availability. Support is operational read-only. Only `operations_admin` may mutate
products, categories, prices or stock. Frontend role checks are usability controls only.
Inventory commands require validated deltas, idempotency and server-side concurrency
controls; movement history is append-only. Do not place credentials, tokens or personal
data in reasons, references, cache entries or event payloads.

The PoC's private Kafka listener is plaintext and unauthenticated, kindnet does not
enforce the declared NetworkPolicies, Kubernetes Secrets are not an external secret
manager, and every workload shares one node/VM. PostgreSQL, Redis and Kafka are all
single-instance services. These controls do not provide host-level high availability or
strong independent security failure domains.

Production requires managed/HA PostgreSQL with backup/PITR and tested failover,
replicated TLS-protected Redis, multi-broker or managed Kafka with TLS and least-privilege
ACLs, multiple Kubernetes nodes/zones, workload identity, external secret rotation,
enforced default-deny network policy, controlled ingress/egress, rate limiting,
autoscaling, audit retention and monitored recovery objectives.

## Order Processing security boundary

Order-service derives cart and order ownership only from the validated Keycloak subject.
It does not accept a customer identity, authoritative price, total or availability from
the browser. Customer cross-resource probes return restricted/not-found behavior;
support is read-only, and only `operations_admin` may invoke explicit state-machine
commands. Order item snapshots, status history and transaction audit are historical
records and must not be rewritten through ordinary application or database operations.

Checkout uses customer-scoped idempotency and Catalogue reservation idempotency to limit
replay and duplicate-order risk. Catalogue row locks and constraints prevent overselling.
Order and Inventory commit in separate databases/services; Saga compensation releases
earlier reservations after partial failure, while unresolved releases remain durable
reconciliation evidence. This is not a distributed ACID transaction, and the PoC has no
automatic durable reconciliation or reservation-expiry worker.

Order outbox messages are delivered at least once. Consumers must deduplicate stable
`event_id` values and must not treat Kafka as authorization or checkout authority. Event,
audit and log payloads exclude JWTs, credentials, payment data and unnecessary PII.
Production requires durable reconciliation workers, resilient idempotent consumers,
stronger service identity and mTLS/private connectivity, managed HA PostgreSQL,
multi-broker Kafka, multi-zone GKE, monitored recovery and tested disaster recovery.
