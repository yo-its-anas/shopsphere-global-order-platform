# Kubernetes

Contains reusable base resources and environment-specific overlays. Configuration should remain declarative, reviewable, and free of embedded secrets. Stateful and secret-dependent workloads are opt-in child overlays, including PostgreSQL, Keycloak, and customer-service.

The customer-service Kubernetes base defines a hardened internal workload and an intended API Gateway-only ingress policy. NetworkPolicy enforcement depends on a compatible CNI and must be tested in each environment.
