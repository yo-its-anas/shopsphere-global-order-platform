# PoC Overlay

Targets the resource-constrained `shopsphere-poc` single-node kind cluster on one Google Cloud VM. Multiple replicas share the same node and physical host, so they do not provide host-level high availability. The root overlay applies namespaces and conservative resource governance.

Stateful components are opt-in child overlays so a missing local Secret cannot cause an incomplete deployment during cluster creation. The [PostgreSQL overlay](postgresql/README.md) deploys the customer and Keycloak logical database foundation after its Kubernetes Secret is created explicitly.

The [Keycloak overlay](keycloak/README.md) deploys the internal identity provider after PostgreSQL is Ready and Keycloak's namespace-scoped Secret has been created explicitly.
