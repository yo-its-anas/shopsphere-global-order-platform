# Catalogue Service Kubernetes Base

Defines a single internal catalogue-service replica, database migration init container, ClusterIP Service, restricted pod/container security contexts, probes, resource bounds, and intended API Gateway-only ingress. Egress is limited to DNS, PostgreSQL, Keycloak JWKS, Redis, and Kafka where NetworkPolicy is enforced.

Readiness depends only on PostgreSQL because it is authoritative for catalogue, pricing, inventory, and the transactional outbox. Redis is a reconstructable cache and degrades to PostgreSQL. Kafka delivery is asynchronous through the recoverable outbox, so broker unavailability retains committed events for retry instead of making synchronous catalogue traffic unready.

Redis is optional at runtime: cache connection failures become misses and do not affect readiness. PostgreSQL remains required and authoritative. One replica on the single-node PoC is not highly available.
