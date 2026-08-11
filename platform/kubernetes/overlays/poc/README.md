# PoC Overlay

Targets the resource-constrained `shopsphere-poc` single-node kind cluster on one Google Cloud VM. Multiple replicas share the same node and physical host, so they do not provide host-level high availability. The root overlay applies namespaces and conservative resource governance.

Stateful components are opt-in child overlays so a missing local Secret cannot cause an incomplete deployment during cluster creation. The [PostgreSQL overlay](postgresql/README.md) deploys the customer and Keycloak logical database foundation after its Kubernetes Secret is created explicitly.

The [Keycloak overlay](keycloak/README.md) deploys the internal identity provider after PostgreSQL is Ready and Keycloak's namespace-scoped Secret has been created explicitly.

The [customer-service overlay](customer-service/README.md) deploys the internal customer capability after PostgreSQL, Keycloak, and its namespace-scoped runtime Secrets are available. It creates no external service endpoint.

The [Redis overlay](redis/README.md) deploys an authenticated internal cache after matching data/application runtime Secrets are created. The [catalogue-service overlay](catalogue-service/README.md) deploys the internal Catalogue and Inventory capability with PostgreSQL authoritative and Redis optional at runtime.

The [Kafka overlay](kafka/README.md) deploys one internal KRaft broker/controller with retained PoC storage. It is opt-in, has no public listener, and provides no broker or host-level high availability.
