# ShopSphere PoC Deployment Guide

This runbook covers the implemented Customer Identity, Product Catalogue/Inventory,
and Enterprise Order Processing workloads on the existing `kind-shopsphere-poc`
cluster. It performs no production
deployment and creates no public service exposure.

## Deployment order

1. Create or reuse the single-node cluster:

   ```bash
   ./platform/kind/create-cluster.sh
   ```

2. Create PostgreSQL credentials, apply the single PostgreSQL instance, reconcile all
   logical databases, and verify it:

   ```bash
   make postgresql-secret
   make validate-postgresql
   make postgresql-apply
   make postgresql-status
   make order-service-secret
   ```

   The final command prepares the namespace-local order-service database URL Secret.

3. Create and verify Keycloak:

   ```bash
   make keycloak-secret
   make validate-keycloak
   make keycloak-apply
   make keycloak-configure
   make keycloak-status
   ```

4. Create Redis credentials and apply the disposable cache:

   ```bash
   make redis-secret
   make validate-redis
   make redis-apply
   make redis-status
   ```

5. Apply the single-broker KRaft Kafka platform and governed topics:

   ```bash
   make validate-kafka
   make kafka-apply
   make kafka-topics
   make kafka-status
   ```

6. Build, load, configure and apply customer-service:

   ```bash
   make customer-service-build
   make customer-service-load
   make customer-service-secret
   make validate-customer-service
   make customer-service-apply
   make customer-service-status
   ```

7. Build, load, configure and apply catalogue-service:

   ```bash
   make catalogue-service-build
   make catalogue-service-load
   make catalogue-service-secret
   make validate-catalogue-service
   make catalogue-service-apply
   make catalogue-service-status
   ```

8. Reconcile the least-privilege order-service identity, then build, load and apply
   order-service:

   ```bash
   make order-service-identity
   make order-service-build
   make order-service-load
   make validate-order-service
   make order-service-apply
   make order-service-status
   ```

9. Build, load and apply API Gateway after all three upstream services are Ready:

   ```bash
   make api-gateway-build
   make api-gateway-load
   make validate-api-gateway
   make api-gateway-apply
   make api-gateway-status
   ```

The service init containers run Alembic before application readiness. Secret helpers
write to Kubernetes without displaying values. Repeated reconciliation preserves
existing PostgreSQL data and credentials.

## Dependency policy

- PostgreSQL is authoritative. Catalogue readiness fails when PostgreSQL is unavailable.
- Redis is a cache-only optimization. Catalogue reads fall back to PostgreSQL and Redis
  does not participate in readiness.
- Kafka receives committed outbox events asynchronously. Broker failure leaves retryable
  outbox rows and does not invalidate a committed catalogue or order transaction.
- Order-service readiness requires PostgreSQL because order state and outbox evidence
  are authoritative there. Catalogue is required for cart validation and checkout, but
  a transient Catalogue failure does not make persisted order-history reads unready.
  Kafka publication is asynchronous and recoverable from the outbox, so Kafka does not
  gate readiness. Keycloak is enforced per authenticated request rather than probed by
  readiness.
- API Gateway readiness reports its synchronous customer/catalogue/order upstream state but
  does not replace downstream JWT or RBAC enforcement.

## Verification

```bash
kubectl --context kind-shopsphere-poc get nodes
kubectl --context kind-shopsphere-poc get deployments,statefulsets,pods,services,pvc -A
make postgresql-status
make keycloak-status
make redis-status
make kafka-status
make customer-service-status
make catalogue-service-status
make order-service-status
make api-gateway-status
make order-service-smoke
```

Current evidence records Ready internal PostgreSQL, Keycloak, Redis, Kafka,
customer-service, catalogue-service, order-service and API Gateway workloads. A
controlled simulated-customer smoke test completed cart creation, Gateway checkout and
cancellation, verified inventory release, and observed `published` state for the four
order outbox events. The explicitly enabled
catalogue integration suite passed all 11 authenticated Gateway/platform scenarios;
Redis and Kafka recovery and post-test readiness were verified. Platform health alone
must still be distinguished from those functional results.

The explicitly enabled Order E2E runner also passed prerequisites and scenarios A–I
through API Gateway using simulated data. It validated successful checkout, insufficient
stock, authoritative repricing, idempotent retry, IDOR protection, concurrent final-unit
integrity, cancellation release, Kafka outbox recovery and Redis fallback. This was an
API-driven run, not a retained browser automation run.

The React frontend is run/built outside Kubernetes in this PoC. Use protected SSH
tunnels and `kubectl port-forward`; do not create NodePort/LoadBalancer resources or
public firewall rules for PostgreSQL, Redis, Kafka, Keycloak administration, Jenkins or
the internal services.

## Availability and production boundary

One PostgreSQL instance/PVC, one ephemeral Redis pod, one Kafka broker/controller/PVC,
one kind node and one physical GCP VM form a single failure domain. This does not provide
host-level high availability.

`customer_db`, `catalogue_db`, `order_db` and `keycloak_db` are logical databases on that
one PostgreSQL server, not independently resilient database services. Customer,
catalogue and order workloads also share the VM. Checkout reserves inventory in
catalogue-service before order-service commits the order; these are separate service
transactions coordinated by idempotency, Saga compensation and retained reconciliation
evidence rather than a distributed database transaction.

Production requires multi-zone GKE with managed load balancing and horizontally scalable
stateless services; managed regional/HA PostgreSQL with encrypted backups, PITR and tested
failover; replicated/managed Redis; managed or multi-broker Kafka across zones; measured
autoscaling; durable reconciliation workers; resilient idempotent event consumers;
external secret management; stronger workload identity and mTLS where appropriate;
private connectivity; enforced network policy; controlled ingress/egress; monitoring;
a deliberate multi-region strategy where business recovery/latency requires it; and
tested disaster recovery.
