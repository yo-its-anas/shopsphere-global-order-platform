# Kubernetes Base

Holds common namespace and safe resource-governance manifests. The root foundation base creates only ShopSphere namespaces, ResourceQuotas, and LimitRanges.

Reusable component bases are kept in child directories and are deployed only when an environment overlay explicitly references them. The `postgresql` component provides the PoC persistence foundation. Redis, Kafka, identity, business services, Jenkins workloads, and monitoring workloads are not deployed by the root base.
