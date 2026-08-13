# Order Service Kubernetes Base

Defines one internal order-service replica, an Alembic migration init container, a
ClusterIP Service, hardened pod/container contexts, probes, bounded resources, rolling
updates, graceful termination, and intended API Gateway-only ingress.

`/health/live` checks only the process. `/health/ready` checks PostgreSQL because
`order_db` is authoritative for carts, orders, history, audit and the transactional
outbox. Catalogue is required by add-to-cart and checkout operations, but a transient
Catalogue failure must not remove order-history reads from service. Kafka is asynchronous:
committed events remain in PostgreSQL for retry, so broker failure does not make the
service unready. Keycloak/JWKS failures affect authenticated requests but are not included
in readiness to avoid restarting an otherwise healthy order data/API process.

The NetworkPolicy expresses API Gateway-only ingress and required DNS, PostgreSQL,
Catalogue, Keycloak and Kafka egress. The default kind `kindnet` environment does not
provide reliable NetworkPolicy enforcement; treat this as policy intent until a compatible
CNI is installed and enforcement is tested.

The single replica runs on one kind node and one physical VM. It is not host-level high
availability.
