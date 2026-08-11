# Kubernetes Base

Holds common namespace and safe resource-governance manifests. The root foundation base creates only ShopSphere namespaces, ResourceQuotas, and LimitRanges.

Reusable component bases are kept in child directories and are deployed only when an environment overlay explicitly references them. PostgreSQL provides persistence, Keycloak provides identity, Redis provides reconstructable caching, and customer/catalogue bases define internal business workloads. Kafka, Jenkins workloads, and monitoring workloads are not deployed by the root base.
