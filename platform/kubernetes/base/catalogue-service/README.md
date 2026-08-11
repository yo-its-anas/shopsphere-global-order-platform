# Catalogue Service Kubernetes Base

Defines a single internal catalogue-service replica, database migration init container, ClusterIP Service, restricted pod/container security contexts, probes, resource bounds, and intended API Gateway-only ingress. Egress is limited to DNS, PostgreSQL, Keycloak JWKS, and Redis where NetworkPolicy is enforced.

Redis is optional at runtime: cache connection failures become misses and do not affect readiness. PostgreSQL remains required and authoritative. One replica on the single-node PoC is not highly available.
