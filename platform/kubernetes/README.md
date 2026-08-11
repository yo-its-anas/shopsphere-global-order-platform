# Kubernetes

Contains reusable base resources and environment-specific overlays. Configuration remains declarative, reviewable, and free of embedded secrets. Runtime-dependent workloads are opt-in child overlays, including PostgreSQL, Keycloak, Redis, customer-service, catalogue-service, and API Gateway.

The customer-service Kubernetes base defines a hardened internal workload and an intended API Gateway-only ingress policy. NetworkPolicy enforcement depends on a compatible CNI and must be tested in each environment.

Redis is an authenticated ClusterIP-only ephemeral cache in `shopsphere-data`; catalogue-service is an internal ClusterIP-only workload in `shopsphere-apps`. Redis has no PVC because all entries are reconstructable from PostgreSQL. Both use restricted security contexts, probes, and PoC resource bounds. The single-node topology is not highly available.

The API Gateway is a ClusterIP-only transport workload in `shopsphere-apps`. It uses fixed customer and catalogue service origins and does not replace downstream JWT/RBAC enforcement. No public Ingress, NodePort, or LoadBalancer is created by this foundation.
